import argparse
import asyncio
import logging
import os
import sqlite3
import time
import uuid
import wave
import numpy as np
import random
from enum import Enum
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import io

import aiofiles
import aiohttp
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 导入 TTS 相关模块
import torch
import soundfile as sf
from chatterbox.mtl_tts import ChatterboxMultilingualTTS, SUPPORTED_LANGUAGES

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设备配置
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"🚀 TTS 服务运行在设备: {DEVICE}")

# 模型配置参数
MODEL_NAME = os.environ.get("MODEL_NAME", "chatterbox-mtl")
TTS_MODEL_PATH = os.environ.get("TTS_MODEL_PATH", None)
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "zh")
MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "300"))
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "10"))
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))
TTS_THREAD_POOL_SIZE = int(os.environ.get("TTS_THREAD_POOL_SIZE", "4"))

# 支持的语言配置
LANGUAGE_CONFIG = {
    "ar": {"name": "Arabic", "default_text": "في الشهر الماضي، وصلنا إلى معلم جديد بمليارين من المشاهدات على قناتنا على يوتيوب."},
    "da": {"name": "Danish", "default_text": "Sidste måned nåede vi en ny milepæl med to milliarder visninger på vores YouTube-kanal."},
    "de": {"name": "German", "default_text": "Letzten Monat haben wir einen neuen Meilenstein erreicht: zwei Milliarden Aufrufe auf unserem YouTube-Kanal."},
    "el": {"name": "Greek", "default_text": "Τον περασμένο μήνα, φτάσαμε σε ένα νέο ορόσημο με δύο δισεκατομμύρια προβολές στο κανάλι μας στο YouTube."},
    "en": {"name": "English", "default_text": "Last month, we reached a new milestone with two billion views on our YouTube channel."},
    "es": {"name": "Spanish", "default_text": "El mes pasado alcanzamos un nuevo hito: dos mil millones de visualizaciones en nuestro canal de YouTube."},
    "fi": {"name": "Finnish", "default_text": "Viime kuussa saavutimme uuden virstanpylvään kahden miljardin katselukerran kanssa YouTube-kanavallamme."},
    "fr": {"name": "French", "default_text": "Le mois dernier, nous avons atteint un nouveau jalon avec deux milliards de vues sur notre chaîne YouTube."},
    "he": {"name": "Hebrew", "default_text": "בחודש שעבר הגענו לאבן דרך חדשה עם שני מיליארד צפיות בערוץ היוטיוב שלנו."},
    "hi": {"name": "Hindi", "default_text": "पिछले महीने हमने एक नया मील का पत्थर छुआ: हमारे YouTube चैनल पर दो अरब व्यूज़।"},
    "it": {"name": "Italian", "default_text": "Il mese scorso abbiamo raggiunto un nuovo traguardo: due miliardi di visualizzazioni sul nostro canale YouTube."},
    "ja": {"name": "Japanese", "default_text": "先月、私たちのYouTubeチャンネルで二十億回の再生回数という新たなマイルストーンに到達しました。"},
    "ko": {"name": "Korean", "default_text": "지난달 우리는 유튜브 채널에서 이십억 조회수라는 새로운 이정표에 도달했습니다."},
    "ms": {"name": "Malay", "default_text": "Bulan lepas, kami mencapai pencapaian baru dengan dua bilion tontonan di saluran YouTube kami."},
    "nl": {"name": "Dutch", "default_text": "Vorige maand bereikten we een nieuwe mijlpaal met twee miljard weergaven op ons YouTube-kanaal."},
    "no": {"name": "Norwegian", "default_text": "Forrige måned nådde vi en ny milepæl med to milliarder visninger på YouTube-kanalen vår."},
    "pl": {"name": "Polish", "default_text": "W zeszłym miesiącu osiągnęliśmy nowy kamień milowy z dwoma miliardami wyświetleń na naszym kanale YouTube."},
    "pt": {"name": "Portuguese", "default_text": "No mês passado, alcançámos um novo marco: dois mil milhões de visualizações no nosso canal do YouTube."},
    "ru": {"name": "Russian", "default_text": "В прошлом месяце мы достигли нового рубежа: два миллиарда просмотров на нашем YouTube-канале."},
    "sv": {"name": "Swedish", "default_text": "Förra månaden nådde vi en ny milstolpe med två miljarder visningar på vår YouTube-kanal."},
    "sw": {"name": "Swahili", "default_text": "Mwezi uliopita, tulifika hatua mpya ya maoni ya bilioni mbili kweny kituo chetu cha YouTube."},
    "tr": {"name": "Turkish", "default_text": "Geçen ay YouTube kanalımızda iki milyar görüntüleme ile yeni bir dönüm noktasına ulaştık."},
    "zh": {"name": "Chinese", "default_text": "上个月，我们达到了一个新的里程碑. 我们的YouTube频道观看次数达到了二十亿次，这绝对令人难以置신。"},
}

# 命令行参数解析
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="0.0.0.0", help="服务监听地址")
parser.add_argument("--port", type=int, default=8001, help="服务监听端口")
parser.add_argument("--model_name", type=str, default=MODEL_NAME, help="TTS模型名称")
parser.add_argument("--model_path", type=str, default=TTS_MODEL_PATH, help="TTS模型路径")
parser.add_argument("--device", type=str, default=DEVICE, help="设备类型")
parser.add_argument("--max_concurrent_tasks", type=int, default=MAX_CONCURRENT_TASKS, help="最大并发任务数")
parser.add_argument("--db_pool_size", type=int, default=DB_POOL_SIZE, help="数据库连接池大小")
parser.add_argument("--tts_thread_pool_size", type=int, default=TTS_THREAD_POOL_SIZE, help="TTS处理线程池大小")
parser.add_argument("--temp_dir", type=str, default="temp_dir/", help="临时文件目录")
parser.add_argument("--output_dir", type=str, default="output_dir/", help="音频输出目录")
args = parser.parse_args()

# 创建必要的目录
os.makedirs(args.temp_dir, exist_ok=True)
os.makedirs(args.output_dir, exist_ok=True)

# 任务状态枚举
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

# 数据库连接池
class DatabaseConnectionPool:
    def __init__(self, db_path=":memory:", pool_size=10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections = []
        self.lock = asyncio.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.append(conn)
    
    async def get_connection(self):
        async with self.lock:
            if self.connections:
                return self.connections.pop()
            else:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                return conn
    
    async def return_connection(self, conn):
        async with self.lock:
            if len(self.connections) < self.pool_size:
                self.connections.append(conn)
            else:
                conn.close()
    
    async def execute(self, query, params=()):
        conn = await self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        finally:
            await self.return_connection(conn)
    
    async def executemany(self, query, params_list):
        conn = await self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor
        finally:
            await self.return_connection(conn)
    
    async def fetchone(self, query, params=()):
        conn = await self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            await self.return_connection(conn)
    
    async def fetchall(self, query, params=()):
        conn = await self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            await self.return_connection(conn)

# 初始化数据库连接池
db_pool = DatabaseConnectionPool(":memory:", args.db_pool_size)

# 创建TTS任务表
async def init_db():
    await db_pool.execute('''
    CREATE TABLE tts_tasks (
        task_id TEXT PRIMARY KEY,
        text_content TEXT,
        language_id TEXT,
        audio_prompt_path TEXT,
        exaggeration REAL DEFAULT 0.5,
        temperature REAL DEFAULT 0.8,
        cfg_weight REAL DEFAULT 0.5,
        seed_num INTEGER DEFAULT 0,
        output_path TEXT,
        status TEXT,
        progress REAL DEFAULT 0,
        error_msg TEXT,
        created_time INTEGER,
        updated_time INTEGER,
        callback_url TEXT,
        callback_status TEXT,
        app_id TEXT,
        biz_type TEXT,
        biz_unique_id TEXT UNIQUE,
        audio_format TEXT DEFAULT 'wav',
        sample_rate INTEGER DEFAULT 22050
    )
    ''')

# 任务队列和并发控制
task_queue = asyncio.Queue()
running_tasks = set()
tts_thread_pool = ThreadPoolExecutor(max_workers=args.tts_thread_pool_size)

# 全局TTS模型
MODEL = None

def set_seed(seed: int):
    """设置随机种子以确保可重现性"""
    torch.manual_seed(seed)
    if args.device == "cuda":
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)

def get_or_load_model():
    """加载TTS模型"""
    global MODEL
    if MODEL is None:
        logger.info("正在初始化TTS模型...")
        try:
            if args.model_path:
                MODEL = ChatterboxMultilingualTTS.from_pretrained(args.model_path, device=args.device)
            else:
                MODEL = ChatterboxMultilingualTTS.from_pretrained(args.device)
            
            if hasattr(MODEL, 'to'):
                MODEL.to(args.device)
            
            logger.info(f"TTS模型加载成功，设备: {getattr(MODEL, 'device', 'N/A')}")
        except Exception as e:
            logger.error(f"加载TTS模型失败: {e}")
            raise
    return MODEL

def generate_tts_audio_sync(
    text_content: str,
    language_id: str,
    audio_prompt_path: Optional[str] = None,
    exaggeration: float = 0.5,
    temperature: float = 0.8,
    cfg_weight: float = 0.5,
    seed_num: int = 0,
    output_path: str = None
) -> Dict[str, Any]:
    """同步TTS音频生成函数"""
    try:
        current_model = get_or_load_model()
        
        if current_model is None:
            raise RuntimeError("TTS模型未加载")
        
        # 设置随机种子
        if seed_num != 0:
            set_seed(int(seed_num))
        
        # 截断文本长度
        text_content = text_content[:MAX_TEXT_LENGTH]
        
        # 准备生成参数
        generate_kwargs = {
            "exaggeration": exaggeration,
            "temperature": temperature,
            "cfg_weight": cfg_weight,
        }
        
        if audio_prompt_path:
            generate_kwargs["audio_prompt_path"] = audio_prompt_path
        
        logger.info(f"开始生成音频: 文本长度={len(text_content)}, 语言={language_id}")
        
        # 生成音频
        wav = current_model.generate(
            text_content,
            language_id=language_id,
            **generate_kwargs
        )
        
        # 获取采样率
        sample_rate = getattr(current_model, 'sr', 22050)
        
        # 保存音频文件
        if output_path:
            sf.write(output_path, wav.squeeze(0).numpy(), sample_rate)
            logger.info(f"音频已保存到: {output_path}")
        
        return {
            "success": True,
            "audio_data": wav.squeeze(0).numpy(),
            "sample_rate": sample_rate,
            "output_path": output_path,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"TTS音频生成失败: {e}")
        return {
            "success": False,
            "audio_data": None,
            "sample_rate": 0,
            "output_path": None,
            "error": str(e)
        }

async def process_tts_task(task_id: str):
    """处理TTS任务"""
    logger.info(f"开始处理TTS任务: {task_id}")
    
    try:
        # 更新任务状态为处理中
        await db_pool.execute(
            "UPDATE tts_tasks SET status = ?, progress = 0.1, updated_time = ? WHERE task_id = ?",
            (TaskStatus.PROCESSING.value, int(time.time()), task_id)
        )
        
        # 获取任务信息
        task_info = await db_pool.fetchone(
            "SELECT * FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not task_info:
            raise Exception("任务信息不存在")
        
        # 提取任务参数
        text_content = task_info["text_content"]
        language_id = task_info["language_id"]
        audio_prompt_path = task_info["audio_prompt_path"]
        exaggeration = task_info["exaggeration"]
        temperature = task_info["temperature"]
        cfg_weight = task_info["cfg_weight"]
        seed_num = task_info["seed_num"]
        output_path = task_info["output_path"]
        
        # 在线程池中执行TTS任务
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            tts_thread_pool,
            generate_tts_audio_sync,
            text_content,
            language_id,
            audio_prompt_path,
            exaggeration,
            temperature,
            cfg_weight,
            seed_num,
            output_path
        )
        
        if result["success"]:
            # 更新任务为完成状态
            await db_pool.execute(
                "UPDATE tts_tasks SET status = ?, progress = 1.0, updated_time = ? WHERE task_id = ?",
                (TaskStatus.COMPLETED.value, int(time.time()), task_id)
            )
            logger.info(f"TTS任务完成: {task_id}")
        else:
            # 更新任务为失败状态
            await db_pool.execute(
                "UPDATE tts_tasks SET status = ?, progress = 0, error_msg = ?, updated_time = ? WHERE task_id = ?",
                (TaskStatus.FAILED.value, result["error"], int(time.time()), task_id)
            )
            logger.error(f"TTS任务失败: {task_id}, 错误: {result['error']}")
        
    except Exception as e:
        logger.error(f"处理TTS任务时发生错误: {e}")
        await db_pool.execute(
            "UPDATE tts_tasks SET status = ?, progress = 0, error_msg = ?, updated_time = ? WHERE task_id = ?",
            (TaskStatus.FAILED.value, str(e), int(time.time()), task_id)
        )

async def task_processor():
    """TTS任务处理器"""
    logger.info("TTS任务处理器已启动")
    
    while True:
        try:
            task_info = await task_queue.get()
            task_id = task_info["task_id"]
            
            # 检查并发任务数
            if len(running_tasks) >= args.max_concurrent_tasks:
                logger.debug(f"并发任务数已达上限，重新放回队列: {task_id}")
                await asyncio.sleep(0.1)
                await task_queue.put(task_info)
                continue
            
            running_tasks.add(task_id)
            
            try:
                await process_tts_task(task_id)
            finally:
                running_tasks.discard(task_id)
                task_queue.task_done()
                
        except Exception as e:
            logger.error(f"任务处理器错误: {e}")

# 启动任务处理器
async def start_task_processor():
    asyncio.create_task(task_processor())

# 初始化FastAPI应用
app = FastAPI(title="Chatterbox TTS")

# 配置模板和静态文件
templates = Jinja2Templates(directory="templates")
app.mount("/output", StaticFiles(directory="output_dir"), name="output")
app.mount("/temp", StaticFiles(directory="temp_dir"), name="temp")

# 音频文件上传处理
@app.post("/upload_audio_prompt")
async def upload_audio_prompt(file: UploadFile = File(...)):
    """上传参考音频文件"""
    try:
        # 验证文件类型
        allowed_extensions = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的音频格式: {file_ext}. 支持的格式: {', '.join(allowed_extensions)}")
        
        # 生成唯一的文件名
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(args.temp_dir, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"音频文件上传成功: {file_path}")
        
        return {
            "code": 0,
            "msg": "音频文件上传成功",
            "file_path": file_path,
            "file_url": f"/temp/{unique_filename}"
        }
    
    except Exception as e:
        logger.error(f"上传音频文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 预定义参考音频文件列表
PREDEFINED_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "data")
@app.get("/list_predefined_audios")
async def list_predefined_audios():
    """列出预定义的参考音频文件"""
    try:
        if not os.path.exists(PREDEFINED_AUDIO_DIR):
            return {
                "code": 0,
                "msg": "预定义音频目录不存在",
                "audios": []
            }
        
        audio_files = []
        for file in os.listdir(PREDEFINED_AUDIO_DIR):
            if file.lower().endswith(('.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg')):
                audio_files.append({
                    "filename": file,
                    "file_path": os.path.join(PREDEFINED_AUDIO_DIR, file),
                    "size": os.path.getsize(os.path.join(PREDEFINED_AUDIO_DIR, file))
                })
        
        return {
            "code": 0,
            "msg": "获取预定义音频列表成功",
            "audios": audio_files
        }
    except Exception as e:
        logger.error(f"获取预定义音频列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 使用预定义参考音频的TTS任务提交
@app.post("/submit_tts_task_with_predefined_audio")
async def submit_tts_task_with_predefined_audio(
    text: str = Form(..., description="要合成的文本"),
    language_id: str = Form(DEFAULT_LANGUAGE, description="语言代码"),
    predefined_audio_filename: str = Form(..., description="预定义音频文件名"),
    exaggeration: float = Form(0.5, description="语音表达度控制 (0.25-2.0)"),
    temperature: float = Form(0.8, description="生成随机性控制 (0.05-5.0)"),
    cfg_weight: float = Form(0.5, description="CFG权重控制 (0.2-1.0)"),
    seed_num: int = Form(0, description="随机种子 (0为随机)"),
    audio_format: str = Form("wav", description="音频格式"),
    sample_rate: int = Form(22050, description="采样率"),
    callback_url: Optional[str] = Form(None, description="任务完成回调URL"),
    app_id: Optional[str] = Form(None, description="应用ID"),
    biz_type: Optional[str] = Form(None, description="业务类型"),
    biz_unique_id: Optional[str] = Form(None, description="业务唯一ID")
):
    """使用预定义参考音频提交TTS任务"""
    try:
        # 验证参数
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=400, detail=f"文本长度不能超过{MAX_TEXT_LENGTH}个字符")
        
        if language_id not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"不支持的语言: {language_id}")
        
        # 验证预定义音频文件是否存在
        predefined_audio_path = os.path.join(PREDEFINED_AUDIO_DIR, predefined_audio_filename)
        if not os.path.exists(predefined_audio_path):
            raise HTTPException(status_code=400, detail=f"预定义音频文件不存在: {predefined_audio_filename}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 生成输出文件路径
        output_filename = f"{task_id}.{audio_format}"
        output_path = os.path.join(args.output_dir, output_filename)
        
        # 创建任务记录，使用预定义音频文件路径
        await db_pool.execute('''
            INSERT INTO tts_tasks (
                task_id, text_content, language_id, audio_prompt_path,
                exaggeration, temperature, cfg_weight, seed_num,
                output_path, status, progress, created_time, updated_time,
                callback_url, callback_status, app_id, biz_type, biz_unique_id,
                audio_format, sample_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, text, language_id, predefined_audio_path,
            exaggeration, temperature, cfg_weight, seed_num,
            output_path, TaskStatus.PENDING.value, 0,
            int(time.time()), int(time.time()),
            callback_url, "pending", app_id, biz_type, biz_unique_id,
            audio_format, sample_rate
        ))
        
        # 添加到任务队列
        await task_queue.put({"task_id": task_id})
        
        logger.info(f"TTS任务已提交: {task_id}, 使用预定义音频: {predefined_audio_path}")
        
        return {
            "code": 0,
            "msg": "任务提交成功",
            "task_id": task_id,
            "output_url": f"/output/{output_filename}",
            "predefined_audio_used": predefined_audio_path
        }
        
    except Exception as e:
        logger.error(f"提交TTS任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    await init_db()
    await start_task_processor()
    
    # 预加载模型
    try:
        get_or_load_model()
        logger.info("TTS服务启动完成")
    except Exception as e:
        logger.error(f"服务启动失败: {e}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "TTS", "version": "1.0.0"}

@app.get("/supported_languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    return {
        "code": 0,
        "languages": SUPPORTED_LANGUAGES,
        "total": len(SUPPORTED_LANGUAGES)
    }

@app.post("/submit_tts_task")
async def submit_tts_task(
    text: str = Form(..., description="要合成的文本"),
    language_id: str = Form(DEFAULT_LANGUAGE, description="语言代码"),
    audio_prompt: Optional[UploadFile] = File(None, description="上传的参考音频文件"),
    audio_prompt_path: Optional[str] = Form(None, description="参考音频文件路径"),
    exaggeration: float = Form(0.5, description="语音表达度控制 (0.25-2.0)"),
    temperature: float = Form(0.8, description="生成随机性控制 (0.05-5.0)"),
    cfg_weight: float = Form(0.5, description="CFG权重控制 (0.2-1.0)"),
    seed_num: int = Form(0, description="随机种子 (0为随机)"),
    audio_format: str = Form("wav", description="音频格式"),
    sample_rate: int = Form(22050, description="采样率"),
    callback_url: Optional[str] = Form(None, description="任务完成回调URL"),
    app_id: Optional[str] = Form(None, description="应用ID"),
    biz_type: Optional[str] = Form(None, description="业务类型"),
    biz_unique_id: Optional[str] = Form(None, description="业务唯一ID")
):
    """提交TTS任务"""
    try:
        # 验证参数
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=400, detail=f"文本长度不能超过{MAX_TEXT_LENGTH}个字符")
        
        if language_id not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"不支持的语言: {language_id}")
        
        # 处理上传的音频文件
        final_audio_prompt_path = audio_prompt_path
        if audio_prompt and audio_prompt.filename:
            # 验证文件类型
            allowed_extensions = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
            file_ext = os.path.splitext(audio_prompt.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                raise HTTPException(status_code=400, detail=f"不支持的音频格式: {file_ext}. 支持的格式: {', '.join(allowed_extensions)}")
            
            # 生成唯一的文件名
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(args.temp_dir, unique_filename)
            
            # 保存文件
            with open(file_path, "wb") as f:
                content = await audio_prompt.read()
                f.write(content)
            
            final_audio_prompt_path = file_path
            logger.info(f"上传的音频文件已保存: {file_path}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 生成输出文件路径
        output_filename = f"{task_id}.{audio_format}"
        output_path = os.path.join(args.output_dir, output_filename)
        
        # 创建任务记录
        await db_pool.execute('''
            INSERT INTO tts_tasks (
                task_id, text_content, language_id, audio_prompt_path,
                exaggeration, temperature, cfg_weight, seed_num,
                output_path, status, progress, created_time, updated_time,
                callback_url, callback_status, app_id, biz_type, biz_unique_id,
                audio_format, sample_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, text, language_id, final_audio_prompt_path,
            exaggeration, temperature, cfg_weight, seed_num,
            output_path, TaskStatus.PENDING.value, 0,
            int(time.time()), int(time.time()),
            callback_url, "pending", app_id, biz_type, biz_unique_id,
            audio_format, sample_rate
        ))
        
        # 添加到任务队列
        await task_queue.put({"task_id": task_id})
        
        logger.info(f"TTS任务已提交: {task_id}")
        
        return {
            "code": 0,
            "msg": "任务提交成功",
            "task_id": task_id,
            "output_url": f"/output/{output_filename}"
        }
        
    except Exception as e:
        logger.error(f"提交TTS任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_tts_status")
async def get_tts_status(task_id: str = Query(..., description="任务ID")):
    """查询TTS任务状态"""
    try:
        result = await db_pool.fetchone(
            "SELECT * FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "code": 0,
            "task_id": task_id,
            "status": result["status"],
            "progress": result["progress"],
            "updated_time": result["updated_time"],
            "callback_status": result["callback_status"],
            "error_msg": result["error_msg"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_tts_result")
async def get_tts_result(task_id: str = Query(..., description="任务ID")):
    """获取TTS任务结果"""
    try:
        result = await db_pool.fetchone(
            "SELECT * FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        response_data = {
            "code": 0,
            "status": result["status"],
            "task_id": task_id,
            "callback_status": result["callback_status"],
            "progress": result["progress"]
        }
        
        if result["status"] == TaskStatus.COMPLETED.value:
            response_data["result"] = {
                "output_path": result["output_path"],
                "output_url": f"/output/{os.path.basename(result['output_path'])}",
                "audio_format": result["audio_format"],
                "sample_rate": result["sample_rate"],
                "text_content": result["text_content"],
                "language_id": result["language_id"]
            }
        elif result["status"] == TaskStatus.FAILED.value:
            response_data["error_msg"] = result["error_msg"]
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download_tts_audio")
async def download_tts_audio(task_id: str = Query(..., description="任务ID")):
    """下载TTS生成的音频文件"""
    try:
        result = await db_pool.fetchone(
            "SELECT * FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if result["status"] != TaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="任务尚未完成")
        
        output_path = result["output_path"]
        if not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        return FileResponse(
            path=output_path,
            media_type=f"audio/{result['audio_format']}",
            filename=os.path.basename(output_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载音频文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_tts_tasks")
async def list_tts_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="任务状态过滤")
):
    """获取TTS任务列表"""
    try:
        offset = (page - 1) * page_size
        
        if status:
            count_result = await db_pool.fetchone(
                "SELECT COUNT(*) as total FROM tts_tasks WHERE status = ?", (status,)
            )
            tasks_result = await db_pool.fetchall(
                "SELECT task_id, text_content, language_id, status, progress, created_time, updated_time, callback_status FROM tts_tasks WHERE status = ? ORDER BY created_time DESC LIMIT ? OFFSET ?",
                (status, page_size, offset)
            )
        else:
            count_result = await db_pool.fetchone(
                "SELECT COUNT(*) as total FROM tts_tasks"
            )
            tasks_result = await db_pool.fetchall(
                "SELECT task_id, text_content, language_id, status, progress, created_time, updated_time, callback_status FROM tts_tasks ORDER BY created_time DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            )
        
        tasks = []
        for row in tasks_result:
            tasks.append({
                "task_id": row["task_id"],
                "text_content": row["text_content"][:50] + "..." if len(row["text_content"]) > 50 else row["text_content"],
                "language_id": row["language_id"],
                "status": row["status"],
                "progress": row["progress"],
                "created_time": row["created_time"],
                "updated_time": row["updated_time"],
                "callback_status": row["callback_status"]
            })
        
        return {
            "code": 0,
            "msg": "查询任务列表成功",
            "tasks": tasks,
            "total": count_result["total"],
            "page": page,
            "limit": page_size
        }
        
    except Exception as e:
        logger.error(f"查询任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel_tts_task")
async def cancel_tts_task(task_id: str = Form(..., description="任务ID")):
    """取消TTS任务"""
    try:
        result = await db_pool.fetchone(
            "SELECT status FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if result["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELED.value]:
            raise HTTPException(status_code=400, detail="任务已结束，无法取消")
        
        await db_pool.execute(
            "UPDATE tts_tasks SET status = ?, updated_time = ? WHERE task_id = ?",
            (TaskStatus.CANCELED.value, int(time.time()), task_id)
        )
        
        return {"code": 0, "msg": "任务取消成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_tts_task")
async def delete_tts_task(task_id: str = Query(..., description="任务ID")):
    """删除TTS任务"""
    try:
        result = await db_pool.fetchone(
            "SELECT output_path FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 删除数据库记录
        await db_pool.execute(
            "DELETE FROM tts_tasks WHERE task_id = ?", (task_id,)
        )
        
        # 删除音频文件
        if result["output_path"] and os.path.exists(result["output_path"]):
            try:
                os.remove(result["output_path"])
            except Exception as e:
                logger.warning(f"删除音频文件失败: {e}")
        
        return {"code": 0, "msg": "任务删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info"
    )