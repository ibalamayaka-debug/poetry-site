import os
import html
import re
import json
import io
import sqlite3
import secrets
from pathlib import Path

try:
    import libsql
except ImportError:
    libsql = None

from flask import Flask, jsonify, render_template, request, send_file

try:
	from opencc import OpenCC
except Exception:
	OpenCC = None

try:
	from hanziconv import HanziConv
except Exception:
	HanziConv = None

try:
	import qrcode
except Exception:
	qrcode = None

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "poetry.db"
DB_PATH = Path(os.environ.get("POETRY_DB_PATH", str(DEFAULT_DB_PATH)))
TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")


def db_available() -> bool:
	if TURSO_URL and TURSO_AUTH_TOKEN:
		return True
	return DB_PATH.exists()


app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    if hasattr(e, 'code'):
        return jsonify({'error': str(e)}), e.code
    return jsonify({'error': 'Server Error: ' + str(e)}), 500

S2T = OpenCC("s2t") if OpenCC else None
T2S = OpenCC("t2s") if OpenCC else None

RAW_CATEGORY_ALIASES = {
	"error": "未分类",
	"json": "未分类",
	"huajianji": "花间集",
	"nantang": "南唐词",
}

DISPLAY_TO_RAW_CATEGORIES: dict[str, set[str]] = {}
for raw_name, display_name in RAW_CATEGORY_ALIASES.items():
	DISPLAY_TO_RAW_CATEGORIES.setdefault(display_name, set()).add(raw_name)


def get_conn():
	url = os.environ.get("TURSO_DATABASE_URL")
	token = os.environ.get("TURSO_AUTH_TOKEN")
	if url and token and libsql:
		conn = libsql.connect(url, auth_token=token)
		return conn

	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def row_to_dict(row, cursor=None):
	if row is None:
		return None
	if hasattr(row, "keys"):
		return dict(row)
	if isinstance(row, dict):
		return dict(row)
	if cursor is not None and getattr(cursor, "description", None):
		cols = [col[0] for col in cursor.description]
		return dict(zip(cols, row))
	return dict(row)


def rows_to_dicts(rows, cursor=None):
	return [row_to_dict(row, cursor) for row in rows]


def table_exists(cursor, table_name: str) -> bool:
	row = cursor.execute(
		"SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
		(table_name,),
	).fetchone()
	return row is not None


def execute_query(query, params=()):
	conn = get_conn()
	cur = conn.cursor()
	cur.execute(query, params)
	rows = cur.fetchall()
	mapped_rows = rows_to_dicts(rows, cur)
	conn.close()
	return mapped_rows

def execute_query_single(query, params=()):
	conn = get_conn()
	cur = conn.cursor()
	cur.execute(query, params)
	row = cur.fetchone()
	mapped_row = row_to_dict(row, cur)
	conn.close()
	return mapped_row

def execute_write(query, params=()):
	conn = get_conn()
	conn.execute(query, params)
	conn.commit()
	conn.close()



def ensure_share_table(conn: sqlite3.Connection) -> None:
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS shared_collections (
			token TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			payload TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			expires_at TEXT
		)
		"""
	)

	# Migrate existing table created before expires_at was introduced.
	cols = conn.execute("PRAGMA table_info(shared_collections)").fetchall()
	col_names = {row[1] for row in cols}
	if "expires_at" not in col_names:
		conn.execute("ALTER TABLE shared_collections ADD COLUMN expires_at TEXT")

	# Backfill legacy rows so old links also have a finite lifetime.
	conn.execute(
		"""
		UPDATE shared_collections
		SET expires_at = datetime(created_at, '+7 days')
		WHERE expires_at IS NULL
		"""
	)


def generate_share_token(conn: sqlite3.Connection) -> str:
	while True:
		token = secrets.token_urlsafe(6)
		exists = conn.execute("SELECT 1 FROM shared_collections WHERE token = ?", (token,)).fetchone()
		if not exists:
			return token


def build_public_share_url(token: str) -> str:
	base = (request.headers.get("X-Forwarded-Proto") or request.scheme) + "://" + (request.headers.get("X-Forwarded-Host") or request.host)
	return f"{base}/s/{token}"


def build_share_qr_png(url: str) -> bytes:
	if qrcode is None:
		raise RuntimeError("qrcode package not installed")
	img = qrcode.make(url)
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	buf.seek(0)
	return buf.getvalue()


def normalize_shared_item(raw: dict) -> dict:
	return {
		"id": int(raw.get("id") or 0),
		"dynasty": to_simplified(str(raw.get("dynasty") or "").strip())[:40],
		"author": to_simplified(str(raw.get("author") or "").strip())[:80],
		"title": to_simplified(str(raw.get("title") or "").strip())[:200],
		"category": to_simplified(str(raw.get("category") or "").strip())[:80],
		"paragraphs": to_simplified(str(raw.get("paragraphs") or "").strip())[:12000],
	}


def parse_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
	try:
		parsed = int(value or default)
	except (TypeError, ValueError):
		parsed = default
	return min(max(parsed, minimum), maximum)


def to_simplified(text: str) -> str:
	if not isinstance(text, str):
		return text
	if T2S is not None:
		return T2S.convert(text)
	if HanziConv is not None:
		try:
			return HanziConv.toSimplified(text)
		except Exception:
			return text
	return text


def category_like(value: str, *names: str) -> bool:
	raw = str(value or "").strip().replace(" ", "")
	sim = to_simplified(raw).replace(" ", "")
	for name in names:
		target = str(name or "").strip().replace(" ", "")
		if not target:
			continue
		if raw == target or sim == target:
			return True
		if target in raw or target in sim:
			return True
	return False


def text_variants(text: str) -> list[str]:
	if not text:
		return []
	variants = {text}
	if S2T is not None:
		variants.add(S2T.convert(text))
	elif HanziConv is not None:
		try:
			variants.add(HanziConv.toTraditional(text))
		except Exception:
			pass
	if T2S is not None:
		variants.add(T2S.convert(text))
	elif HanziConv is not None:
		try:
			variants.add(HanziConv.toSimplified(text))
		except Exception:
			pass
	return [v for v in variants if v]


def punctuate_siku_text(text: str) -> str:
	if not text:
		return text

	def punctuate_line(line: str) -> str:
		line = line.strip()
		if not line:
			return ""
		if re.search(r"[，。！？；：]", line):
			return line

		parts: list[str] = []
		i = 0
		while i < len(line):
			remain = len(line) - i
			if remain <= 14:
				parts.append(line[i:])
				break
			step = 12 if remain > 26 else 10
			parts.append(line[i:i + step] + "，")
			i += step

		merged = "".join(parts).rstrip("，")
		if merged and merged[-1] not in "。！？；":
			merged += "。"
		return merged

	result: list[str] = []
	for raw_line in text.split("\n"):
		line = raw_line.strip()
		if not line:
			continue
		if re.search(r"[。！？；]", line):
			pieces = re.split(r"(?<=[。！？；])", line)
			for piece in pieces:
				piece = piece.strip()
				if piece:
					result.append(piece)
			continue
		result.append(punctuate_line(line))

	return "\n".join(result)


def is_nalan_author(author: str) -> bool:
	a = to_simplified(str(author or "")).replace(" ", "")
	return "纳兰性德" in a or "纳兰容若" in a


def is_liqingzhao_author(author: str) -> bool:
	a = to_simplified(str(author or "")).replace(" ", "")
	return "李清照" in a


def build_liqingzhao_appreciation_short(title: str, paragraphs: str) -> str:
	t = to_simplified(str(title or "")).strip()
	p = to_simplified(str(paragraphs or "")).strip()
	tag = "婉约"
	if any(k in p for k in ["酒", "醉", "黄昏"]):
		tag = "幽婉"
	if any(k in p for k in ["愁", "泪", "断", "凉", "寒"]):
		tag = "凄清"
	if any(k in p for k in ["秋", "梧桐", "雁", "西风"]):
		tag = "清冷"
	if any(k in p for k in ["国", "江山", "北", "南渡"]):
		tag = "家国"

	line = "这首词以细密意象推进情绪，由景入情，层层递进，体现李清照" + tag + "词风。"
	line2 = "语言看似平淡却极有张力，常以口语化句法写出深层心绪，读来含蓄而有回味。"
	if t:
		line = f"《{t}》以细密意象推进情绪，由景入情，层层递进，体现李清照{tag}词风。"

	if any(k in p for k in ["花", "叶", "香", "雨"]):
		line2 = "词中以花、香、风雨等日常景物承载情感转折，语短而意长，形成柔中见峭的表达。"
	if any(k in p for k in ["愁", "泪", "独", "无人"]):
		line2 = "其高明处在于把“愁”写得可感可见，不直白喊苦，而以动作与物象映出内心孤独。"

	return line + line2


def build_liqingzhao_appreciation_detailed(title: str, paragraphs: str) -> str:
	t = to_simplified(str(title or "")).strip()
	p = to_simplified(str(paragraphs or "")).strip()

	part1 = "词中常先写可见之景，再落入不可见之情，形成由外而内的心理推进。"
	part2 = "意象选择多为花、月、风、雨、雁、梧桐等，借景不在铺陈，而在托情。"
	part3 = "句法上短句与复沓并用，语气绵密，既有口语亲近感，又有节奏上的顿挫。"
	part4 = "读者感到的不是单一悲苦，而是时间流逝、身世变化与个体情感交织后的复合哀感。"

	if any(k in p for k in ["酒", "醉"]):
		part2 = "词中酒意并非单写宴饮，而是借“微醺与清醒”之间的摇摆，折射内心难言的波动。"
	if any(k in p for k in ["秋", "西风", "雁"]):
		part4 = "全词以秋意为底色，借冷色意象层层加深情绪，结尾往往以一字或一问收束，余味悠长。"
	if any(k in p for k in ["愁", "泪", "独"]):
		part1 = "词作并不直陈哀怨，而是通过动作细节和环境变化，让“愁”在阅读中慢慢显形。"

	header = f"《{t}》" if t else "本词"
	return header + "" + part1 + part2 + part3 + part4


LIQINGZHAO_BAIHUA_BY_INICIPIT = {
	"绣面芙蓉一笑开": "她笑起来像刚绽放的芙蓉，面容明艳动人；斜斜的发饰映着香腮，眼波才轻轻一转，就已惹人心动。她风姿天然、韵致深长，把半幅写满相思与幽怨的笺纸寄给心上人；待到月色西移、花影摇动时，再悄悄相约重逢。",
	"寻寻觅觅": "我反复寻觅，眼前却只剩冷清与凄苦；天气忽暖忽寒，最难调养。几杯淡酒也挡不住傍晚急风，雁阵飞过，更勾起旧日伤心。满地黄花无人可摘，我独守窗前，觉得天黑得格外漫长；梧桐细雨一直下到黄昏，这般情状，又哪里是一个“愁”字说得尽。",
	"红藕香残玉簟秋": "荷花凋尽、香气将歇，竹席上已透秋凉；我轻解罗裳，独自登舟。云中谁寄来锦书？雁字回时，月光正满西楼。花自飘零、水自流去，我们彼此相思，却分隔两地；这种无从排遣的愁绪，才下眉头，又上心头。",
	"薄雾浓云愁永昼": "薄雾浓云让白日也显得漫长，我在瑞脑香里打发时光。重阳又至，枕席纱帐都透着凉意。黄昏后东篱把酒，暗香盈袖，却无人共赏；若问我为何消瘦，只因这西风里的黄花，也比不上我心头的愁。",
	"昨夜雨疏风骤": "昨夜风急雨疏，浓睡之后酒意还没完全消散。我问卷帘的侍女，海棠花怎么样了，她却说花还同昨夜一般。其实并非如此，应是绿叶更盛、红花更少了。",
	"常记溪亭日暮": "我常常想起那次在溪亭游玩到日暮，兴致太浓，竟忘了归路。船误入藕花深处，惊起一滩鸥鹭。那份明快与天真，如今想来仍鲜活可感。",
	"蹴罢秋千": "荡完秋千，她纤手微露，衣衫沾着薄汗。见有客来，连袜带钗匆匆走避，临去却又倚门回望，含羞地嗅着青梅。少女情态在欲避还看之间，被写得灵动又细腻。",
	"风住尘香花已尽": "风停了，花也落尽，只剩尘土里淡淡残香。她懒得梳头，满怀倦意。想尽兴出游，却担心双溪的小船，载不动自己这许多愁绪。",
}


def build_liqingzhao_translation(title: str, paragraphs: str) -> str:
	_ = to_simplified(str(title or "")).strip()
	p = to_simplified(str(paragraphs or "")).strip()
	lines = [x.strip() for x in re.split(r"[\n。！？；]", p) if x.strip()]
	if not lines:
		return ""

	incipit = lines[0]
	for key, val in LIQINGZHAO_BAIHUA_BY_INICIPIT.items():
		if key in incipit:
			return "白话：" + val

	translated: list[str] = []
	for line in lines[:8]:
		seg = line
		seg = seg.replace("兮", "啊")
		seg = seg.replace("其", "那")
		seg = seg.replace("怎", "怎么")
		seg = seg.replace("何", "什么")
		seg = seg.replace("谁", "谁能") if "谁" in seg else seg
		seg = seg.replace("却", "却又") if "却" in seg else seg
		seg = seg.replace("最难将息", "最难调养休息")
		seg = seg.replace("乍暖还寒", "天气忽暖忽冷")
		seg = seg.replace("怎一个", "哪里是一个")
		seg = seg.replace("了得", "说得尽")
		seg = seg.replace("才下眉头", "刚从眉间散去")
		seg = seg.replace("却上心头", "又立刻涌上心头")
		seg = seg.replace("独上", "独自登上")
		seg = seg.replace("不道", "没想到")
		seg = seg.replace("应是", "大概是")
		seg = seg.replace("绿肥红瘦", "绿叶繁茂而红花稀少")

		# Force paraphrase tone instead of line-by-line literal echo.
		if len(seg) >= 10:
			seg = "词人写到" + seg
		else:
			seg = "她感到" + seg
		translated.append(seg)

	return "白话：" + "；".join(translated) + "。"


def punctuate_nalan_text(text: str) -> str:
	if not text:
		return text

	def punctuate_segment(seg: str) -> str:
		seg = seg.strip()
		if not seg:
			return ""
		if len(seg) <= 10:
			return seg

		step = 7 if len(seg) >= 14 else 5
		chunks = [seg[i:i + step] for i in range(0, len(seg), step) if seg[i:i + step]]
		if len(chunks) <= 1:
			return seg

		built: list[str] = []
		for i, c in enumerate(chunks, start=1):
			if i == len(chunks):
				built.append(c)
			elif i % 2 == 0:
				built.append(c + "。")
			else:
				built.append(c + "，")
		return "".join(built)

	content = to_simplified(str(text))
	content = content.replace("\r\n", "\n")
	content = re.sub(r"[ ]+", "", content)
	content = content.replace(";", "；").replace(",", "，").replace("?", "？").replace("!", "！")

	lines = [x.strip() for x in content.split("\n") if x.strip()]
	if not lines:
		lines = [content.strip()] if content.strip() else []

	result: list[str] = []
	for line in lines:
		if not line:
			continue
		if re.search(r"[，。！？；]", line):
			parts = [x for x in re.split(r"([，。！？；])", line) if x]
			rebuilt: list[str] = []
			i = 0
			while i < len(parts):
				seg = parts[i]
				next_punc = parts[i + 1] if i + 1 < len(parts) and re.fullmatch(r"[，。！？；]", parts[i + 1]) else ""
				seg_fixed = punctuate_segment(seg)
				if next_punc:
					rebuilt.append(seg_fixed + next_punc)
					i += 2
				else:
					rebuilt.append(seg_fixed)
					i += 1
			line = "".join(rebuilt)
			line = re.sub(r"[，。！？；]{2,}", lambda m: m.group(0)[-1], line)
			if line and line[-1] not in "。！？；":
				line += "。"
			result.append(line)
			continue

		# For unpunctuated ci lines, split once near the middle, then close with period.
		if len(line) >= 10:
			mid = len(line) // 2
			cut = mid
			if mid > 3:
				for delta in range(0, 4):
					for cand in (mid - delta, mid + delta):
						if 3 <= cand < len(line) - 2:
							cut = cand
							break
					else:
						continue
					break
			line = line[:cut] + "，" + line[cut:]

		if line[-1] not in "。！？；":
			line += "。"
		result.append(line)

	return "\n".join(result)


def clean_paragraphs_for_display(text: str, category: str, author: str = "") -> str:
	if not isinstance(text, str):
		return text
	if category_like(category, "黄帝内经", "黃帝內經"):
		cleaned = html.unescape(text)
		cleaned = cleaned.replace("\r\n", "\n")
		cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
		cleaned = re.sub(r"</p>\s*", "\n", cleaned, flags=re.IGNORECASE)
		cleaned = re.sub(r"<p[^>]*>", "", cleaned, flags=re.IGNORECASE)
		cleaned = re.sub(r"<img[^>]*>", "", cleaned, flags=re.IGNORECASE)
		cleaned = re.sub(r"<[^>]+>", "", cleaned)

		filtered_lines: list[str] = []
		for raw_line in cleaned.split("\n"):
			line = raw_line.strip()
			if not line:
				continue
			line = re.sub(r"\s+[A-Za-z_]{1,12}$", "", line).strip()
			if line in {"文字颜色样式示例", "返回目录"}:
				continue
			if re.fullmatch(r"[A-Za-z_]{1,12}", line):
				continue
			filtered_lines.append(line)

		return to_simplified("\n".join(filtered_lines))

	if category_like(category, "四库全书", "四庫全書"):
		cleaned = html.unescape(text)
		cleaned = cleaned.replace("\r\n", "\n")
		cleaned = re.sub(r"\bThis document is published under[^\n]*", " ", cleaned, flags=re.IGNORECASE)
		cleaned = re.sub(r"\bXXX\b", " ", cleaned)
		cleaned = re.sub(r"[A-Za-z][A-Za-z\s\-:;,\.]{2,}", " ", cleaned)
		cleaned = re.sub(r"\s+", " ", cleaned).strip()

		# Fix XML tokenization where each Han character is separated by spaces.
		cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", cleaned)
		cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[（(])", "", cleaned)
		cleaned = re.sub(r"(?<=[)）])\s+(?=[\u4e00-\u9fff])", "", cleaned)
		cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。！？；：])", "", cleaned)
		cleaned = re.sub(r"(?<=[，。！？；：])\s+(?=[\u4e00-\u9fff])", "", cleaned)
		cleaned = to_simplified(cleaned)
		cleaned = punctuate_siku_text(cleaned)

		# Add readable line breaks: punctuation first, then fixed-width fallback.
		cleaned = re.sub(r"([。！？；])", r"\1\n", cleaned)
		lines: list[str] = []
		for raw_line in cleaned.split("\n"):
			line = raw_line.strip()
			if not line:
				continue
			if len(line) <= 36:
				lines.append(line)
				continue
			start = 0
			while start < len(line):
				end = min(start + 20, len(line))
				lines.append(line[start:end])
				start = end

		return "\n".join(lines).strip()

	result = to_simplified(text)
	if is_nalan_author(author):
		result = punctuate_nalan_text(result)
	return result


def simplify_poem_row(row: dict) -> dict:
	category = display_category(row["category"])
	author = to_simplified(row["author"])
	title = to_simplified(row["title"])
	paragraphs = clean_paragraphs_for_display(row["paragraphs"], category, row["author"])
	appreciation_short = build_liqingzhao_appreciation_short(title, paragraphs) if is_liqingzhao_author(author) else ""
	appreciation_detailed = build_liqingzhao_appreciation_detailed(title, paragraphs) if is_liqingzhao_author(author) else ""
	translation_baihua = build_liqingzhao_translation(title, paragraphs) if is_liqingzhao_author(author) else (row.get("translation_baihua") or "")
	return {
		"id": row["id"],
		"dynasty": to_simplified(row["dynasty"]),
		"author": author,
		"title": title,
		"paragraphs": paragraphs,
		"category": category,
		"appreciation": row.get("appreciation") or appreciation_short,
		"appreciation_short": appreciation_short,
		"appreciation_detailed": appreciation_detailed,
		"translation_baihua": translation_baihua,
	}


def display_category(category: str) -> str:
	if not isinstance(category, str):
		return category
	key = category.lower()
	if key in RAW_CATEGORY_ALIASES:
		return RAW_CATEGORY_ALIASES[key]
	return to_simplified(category)


def category_variants_for_filter(value: str) -> list[str]:
	base_variants = set(text_variants(value))
	expanded = set(base_variants)

	for variant in list(base_variants):
		simplified_variant = to_simplified(variant)
		raws = DISPLAY_TO_RAW_CATEGORIES.get(variant, set())
		raws |= DISPLAY_TO_RAW_CATEGORIES.get(simplified_variant, set())
		expanded |= raws

		alias = RAW_CATEGORY_ALIASES.get(variant.lower())
		if alias:
			expanded.add(alias)

	return [x for x in expanded if x]


@app.get("/")
def index():
	return render_template("index.html")


@app.get("/s/<token>")
def shared_collection_page(token: str):
	if not db_available():
		return "数据库不存在", 400

	conn = get_conn()
	ensure_share_table(conn)
	conn.execute("DELETE FROM shared_collections WHERE expires_at <= datetime('now')")
	conn.commit()
	cur = conn.execute(
		"SELECT token, name, payload, created_at, expires_at FROM shared_collections WHERE token = ?",
		(token,),
	)
	row = row_to_dict(cur.fetchone(), cur)
	conn.close()

	if not row:
		return "分享链接不存在或已失效", 404

	try:
		items = json.loads(row["payload"])
		if not isinstance(items, list):
			items = []
	except Exception:
		items = []

	share_url = build_public_share_url(token)
	description_text = f"{to_simplified(row['name'])}，共 {len(items)} 条古诗词收藏，可打开查看与转发。"
	preview_titles = [normalize_shared_item(x).get("title", "") for x in items[:4] if isinstance(x, dict)]
	qr_src = f"/api/share-qr/{token}"

	return render_template(
		"shared.html",
		token=token,
		share_url=share_url,
		description_text=description_text,
		preview_titles=preview_titles,
		qr_src=qr_src,
		collection_name=to_simplified(row["name"]),
		created_at=row["created_at"],
		expires_at=row["expires_at"],
		items=[normalize_shared_item(x) for x in items if isinstance(x, dict)],
	)


@app.get("/api/share-qr/<token>")
def shared_collection_qr(token: str):
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	conn = get_conn()
	ensure_share_table(conn)
	row = conn.execute(
		"SELECT token FROM shared_collections WHERE token = ? AND expires_at > datetime('now')",
		(token,),
	).fetchone()
	conn.close()
	if not row:
		return jsonify({"error": "分享链接不存在或已失效"}), 404

	png = build_share_qr_png(build_public_share_url(token))
	return send_file(io.BytesIO(png), mimetype="image/png")


@app.get("/api/search")
def search_poetry():
	if not db_available():
		return jsonify({"error": "数据库不存在，请先运行 scripts/build_poetry_db.py 构建 poetry.db"}), 400

	q = (request.args.get("q") or "").strip()
	dynasty = (request.args.get("dynasty") or "").strip()
	author = (request.args.get("author") or "").strip()
	category = (request.args.get("category") or "").strip()
	dedupe = (request.args.get("dedupe") or "1").strip().lower() not in {"0", "false", "no"}
	page = parse_int(request.args.get("page"), default=1, minimum=1, maximum=1000000)
	page_size = parse_int(request.args.get("page_size"), default=20, minimum=1, maximum=50)
	offset = (page - 1) * page_size

	where_parts = []
	params: list[object] = []
	conn = get_conn()
	cur = conn.cursor()
	has_fts = table_exists(cur, "poems_fts")

	if q:
		q_variants = [v.replace('"', "") for v in text_variants(q)]
		like_parts = []
		for _ in q_variants:
			like_parts.append("poems.title LIKE ?")
			like_parts.append("poems.paragraphs LIKE ?")

		search_parts = []
		if has_fts:
			match_parts = ["poems_fts MATCH ?" for _ in q_variants]
			fts_clause = "poems.id IN (SELECT rowid FROM poems_fts WHERE " + " OR ".join(match_parts) + ")"
			search_parts.append(fts_clause)
			params.extend([f'"{v}"' for v in q_variants])

		search_parts.extend(like_parts)
		where_parts.append("(" + " OR ".join(search_parts) + ")")
		for v in q_variants:
			params.append(f"%{v}%")
			params.append(f"%{v}%")
	if dynasty:
		dynasty_variants = text_variants(dynasty)
		placeholders = ",".join(["?" for _ in dynasty_variants])
		where_parts.append(f"poems.dynasty IN ({placeholders})")
		params.extend(dynasty_variants)
	if author:
		author_variants = [v.replace('"', "") for v in text_variants(author)]
		if has_fts:
			author_parts = ["poems_fts MATCH ?" for _ in author_variants]
			where_parts.append("poems.id IN (SELECT rowid FROM poems_fts WHERE " + " OR ".join(author_parts) + ")")
			params.extend([f"author:{v}" for v in author_variants])
		else:
			author_parts = ["poems.author LIKE ?" for _ in author_variants]
			where_parts.append("(" + " OR ".join(author_parts) + ")")
			params.extend([f"%{v}%" for v in author_variants])
	if category:
		category_variants = category_variants_for_filter(category)
		placeholders = ",".join(["?" for _ in category_variants])
		where_parts.append(f"poems.category IN ({placeholders})")
		params.extend(category_variants)

	where_sql = ""
	if where_parts:
		where_sql = "WHERE " + " AND ".join(where_parts)

	if dedupe:
		count_sql = f"""
			WITH filtered AS (
				SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
				FROM poems
				{where_sql}
			), ranked AS (
				SELECT *,
					ROW_NUMBER() OVER (
						PARTITION BY title, paragraphs
						ORDER BY id DESC
					) AS rn
				FROM filtered
			)
			SELECT COUNT(*) FROM ranked WHERE rn = 1
		"""
		total = cur.execute(count_sql, params).fetchone()[0]

		query_sql = f"""
			WITH filtered AS (
				SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
				FROM poems
				{where_sql}
			), ranked AS (
				SELECT *,
					ROW_NUMBER() OVER (
						PARTITION BY title, paragraphs
						ORDER BY id DESC
					) AS rn
				FROM filtered
			)
			SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
			FROM ranked
			WHERE rn = 1
			ORDER BY id DESC
			LIMIT ? OFFSET ?
		"""
		rows = cur.execute(query_sql, [*params, page_size, offset]).fetchall()
	else:
		count_sql = f"SELECT COUNT(*) FROM poems {where_sql}"
		total = cur.execute(count_sql, params).fetchone()[0]

		query_sql = f"""
			SELECT id, dynasty, author, title, paragraphs, category, translation_baihua, appreciation
			FROM poems
			{where_sql}
			ORDER BY id DESC
			LIMIT ? OFFSET ?
		"""
		rows = cur.execute(query_sql, [*params, page_size, offset]).fetchall()
	items = rows_to_dicts(rows, cur)
	conn.close()

	return jsonify({"page": page, "page_size": page_size, "total": total, "items": [simplify_poem_row(r) for r in items]})


@app.get("/api/authors")
def suggest_authors():
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	q = (request.args.get("q") or "").strip()
	limit = parse_int(request.args.get("limit"), default=8, minimum=1, maximum=20)

	conn = get_conn()
	cur = conn.cursor()
	if q:
		rows = cur.execute(
			"""
			SELECT author, COUNT(*) AS cnt
			FROM poems
			WHERE author LIKE ?
			GROUP BY author
			ORDER BY cnt DESC, author ASC
			LIMIT ?
			""",
			(f"%{q}%", limit),
		).fetchall()
	else:
		rows = cur.execute(
			"""
			SELECT author, COUNT(*) AS cnt
			FROM poems
			GROUP BY author
			ORDER BY cnt DESC, author ASC
			LIMIT ?
			""",
			(limit,),
		).fetchall()
	items = rows_to_dicts(rows, cur)
	conn.close()
	return jsonify({"items": [{"author": to_simplified(r["author"]), "cnt": r["cnt"]} for r in items]})


@app.get("/api/stats/dynasty")
def stats_dynasty():
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	conn = get_conn()
	cur = conn.cursor()
	rows = cur.execute(
		"""
		SELECT dynasty, COUNT(*) AS cnt
		FROM poems
		GROUP BY dynasty
		ORDER BY cnt DESC, dynasty ASC
		"""
	).fetchall()
	items = rows_to_dicts(rows, cur)
	conn.close()
	return jsonify({"items": [{"dynasty": to_simplified(r["dynasty"]), "cnt": r["cnt"]} for r in items]})


@app.get("/api/categories")
def categories():
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	conn = get_conn()
	cur = conn.cursor()
	rows = cur.execute(
		"""
		SELECT category, COUNT(*) AS cnt
		FROM poems
		GROUP BY category
		ORDER BY cnt DESC, category ASC
		"""
	).fetchall()
	rows = rows_to_dicts(rows, cur)
	conn.close()

	merged: dict[str, int] = {}
	for row in rows:
		display_name = display_category(row["category"])
		merged[display_name] = merged.get(display_name, 0) + int(row["cnt"])

	items = [{"category": name, "cnt": cnt} for name, cnt in merged.items()]
	items.sort(key=lambda x: (-x["cnt"], x["category"]))
	return jsonify({"items": items})


@app.post("/api/share-collection")
def create_share_collection():
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	body = request.get_json(silent=True) or {}
	name = to_simplified(str(body.get("name") or "默认收藏夹").strip())[:80]
	raw_items = body.get("items")
	if not isinstance(raw_items, list) or not raw_items:
		return jsonify({"error": "收藏夹为空，无法生成链接"}), 400
	if len(raw_items) > 300:
		return jsonify({"error": "收藏条目过多，请控制在 300 条以内"}), 400

	items = [normalize_shared_item(x) for x in raw_items if isinstance(x, dict)]
	items = [x for x in items if x["title"] and x["paragraphs"]]
	if not items:
		return jsonify({"error": "收藏内容无效，无法生成链接"}), 400

	payload = json.dumps(items, ensure_ascii=False)
	if len(payload) > 2_000_000:
		return jsonify({"error": "收藏内容过大，无法生成链接"}), 400

	conn = get_conn()
	ensure_share_table(conn)
	conn.execute("DELETE FROM shared_collections WHERE expires_at <= datetime('now')")
	token = generate_share_token(conn)
	conn.execute(
		"INSERT INTO shared_collections(token, name, payload, expires_at) VALUES (?, ?, ?, datetime('now', '+7 days'))",
		(token, name, payload),
	)
	conn.commit()
	cur = conn.execute("SELECT expires_at FROM shared_collections WHERE token = ?", (token,))
	row = row_to_dict(cur.fetchone(), cur)
	conn.close()

	url = build_public_share_url(token)
	return jsonify({"token": token, "url": url, "expires_at": row["expires_at"] if row else None})

@app.post("/api/translation")
def add_translation():
	if not db_available():
		return jsonify({"error": "数据库不存在"}), 400

	body = request.get_json(silent=True) or {}
	poem_id = body.get("id")
	translation = body.get("translation")

	if not poem_id or translation is None:
		return jsonify({"error": "缺少必须的参数: id 和 translation"}), 400

	try:
		poem_id = int(poem_id)
	except ValueError:
		return jsonify({"error": "id 必须是整数"}), 400

	conn = get_conn()
	cur = conn.cursor()
	
	cur.execute("SELECT id FROM poems WHERE id = ?", (poem_id,))
	if not cur.fetchone():
		conn.close()
		return jsonify({"error": "找不到指定的诗词"}), 404

	cur.execute("UPDATE poems SET translation_baihua = ? WHERE id = ?", (str(translation).strip(), poem_id))
	conn.commit()
	conn.close()

	return jsonify({"message": "翻译添加成功"})


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)



if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

# Vercel Deployment
application = app
handler = app
