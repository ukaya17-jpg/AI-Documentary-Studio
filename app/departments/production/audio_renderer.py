"""Audio (TTS) stage: synthesize narration and a matching subtitle file.

Thin wrapper around the legacy app.services.voice tts()/create_subtitle(),
reused as-is, not reimplemented.
"""

import os

from app.config import characters
from app.config.profile_dimensions import Format
from app.models.audio import AudioPlan, AudioTrack
from app.models.character import CharacterReference
from app.models.script import Script
from app.services import voice
from app.utils import utils

# "Varsayılan/Yedek Anlatıcı" planı (kullanıcı onaylı): Kids formatında,
# Auto kadrolamanın bir sahneye YA hiç karakter YA DA (Çoklu Karakter Aynı
# Sahnede planıyla) 2+ karakter atadığı -- yani hangi sesin okuyacağı
# BELİRSİZ olduğu -- durumlarda Professor Nova varsayılan anlatıcı olarak
# kullanılır. Kullanıcının kendi seçimi (registry'deki 5 karakterden
# "anlatıcı" rolüne en nötr/uygun olanı). Kids DIŞINDA bu varsayılan HİÇ
# uygulanmaz -- bkz. _resolve_scene_voice.
_KIDS_DEFAULT_NARRATOR_SLUG = "professor_nova"


def render_narration(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
) -> AudioTrack:
    task_directory = utils.task_dir(task_id)
    audio_file = os.path.join(task_directory, "audio.mp3")
    subtitle_file = os.path.join(task_directory, "subtitle.srt")

    sub_maker = voice.tts(
        text=script.full_text,
        voice_name=voice.parse_voice_name(voice_name),
        voice_rate=voice_rate,
        voice_file=audio_file,
        voice_volume=voice_volume,
    )
    if sub_maker is None:
        raise RuntimeError(
            "failed to synthesize narration audio; check the selected voice and TTS connectivity"
        )

    duration_seconds = voice.get_audio_duration(sub_maker)
    voice.create_subtitle(sub_maker, script.full_text, subtitle_file)

    return AudioTrack(
        voice_name=voice_name,
        voice_file=audio_file,
        subtitle_file=subtitle_file if os.path.exists(subtitle_file) else "",
        duration_seconds=duration_seconds,
    )


def _voice_for_slug_or_none(slug: str | None) -> str | None:
    if not slug:
        return None
    try:
        return characters.get_character_voice_name(slug)
    except KeyError:
        return None


def _resolve_scene_voice(
    voice_name: str,
    casting_by_scene: dict[int, dict] | None,
    scene_index: int,
    format: Format | None = None,
) -> str:
    """"Sahne Bazlı Gerçek Ses Değişimi" + "Çoklu Karakter Aynı Sahnede" +
    "Varsayılan Anlatıcı" planları (kullanıcı onaylı) -- tek fonksiyonda:

    - TAM OLARAK 1 karakter atanmışsa: o karakterin kendi sesi.
    - 2+ karakter atanmışsa (hangi sesin okuyacağı BELİRSİZ): Kids formatında
      _KIDS_DEFAULT_NARRATOR_SLUG (Professor Nova), diğer formatlarda
      listenin İLK karakteri (casting_generator'ın kendi öncelik sırası).
    - Hiç karakter atanmamışsa: Kids formatında yine Professor Nova,
      diğer formatlarda genel `voice_name` (REGRESYON GARANTİSİ -- Kids
      DIŞINDA bu fonksiyonun eklediği TEK davranış, karakter sayısı 1 iken
      zaten var olan orijinal davranıştır).
    - Her adımda, seçilen slug registry'de yoksa (KeyError) bir sonraki
      seçeneğe sessizce düşülür, en kötü ihtimalle `voice_name`'e biter.
    """
    character_slugs = [
        slug
        for slug in (casting_by_scene or {}).get(scene_index, {}).get("characters", [])
        if slug
    ]

    if len(character_slugs) == 1:
        resolved = _voice_for_slug_or_none(character_slugs[0])
        if resolved:
            return resolved
    elif len(character_slugs) >= 2:
        if format == Format.kids:
            resolved = _voice_for_slug_or_none(_KIDS_DEFAULT_NARRATOR_SLUG)
            if resolved:
                return resolved
        resolved = _voice_for_slug_or_none(character_slugs[0])
        if resolved:
            return resolved
    elif format == Format.kids:
        resolved = _voice_for_slug_or_none(_KIDS_DEFAULT_NARRATOR_SLUG)
        if resolved:
            return resolved

    return voice_name


def render_narration_by_scene(
    script: Script,
    task_id: str,
    voice_name: str,
    casting_by_scene: dict[int, dict],
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    format: Format | None = None,
) -> AudioTrack:
    """Same external contract as render_narration() (one AudioTrack covering
    the WHOLE script), but synthesizes each script.lines[i] SEPARATELY,
    using that scene's Auto-cast character's own registered voice (or the
    Kids-format default narrator / general voice_name fallback -- see
    _resolve_scene_voice's docstring for the full priority order) -- then
    concatenates the per-scene audio into one continuous audio.mp3 and
    merges the per-scene subtitle cues (each anchored to that scene's own
    real, measured TTS duration) into one subtitle.srt via
    voice.merge_scene_subtitles().

    Only called by render_audio_plan() when per-scene rendering is actually
    worthwhile (see _should_use_per_scene_narration) -- every other case
    (no Auto casting, non-Auto fixed/no character) keeps using the original
    single-call render_narration(), so those projects are byte-for-byte
    unaffected by this function's existence.
    """
    from pydub import AudioSegment

    task_directory = utils.task_dir(task_id)
    audio_file = os.path.join(task_directory, "audio.mp3")
    subtitle_file = os.path.join(task_directory, "subtitle.srt")

    configured_ffmpeg = utils.get_ffmpeg_binary()
    if configured_ffmpeg:
        AudioSegment.converter = configured_ffmpeg

    combined_audio = AudioSegment.empty()
    scene_subtitle_files: list[tuple[str, float]] = []
    scene_temp_files: list[str] = []
    cumulative_seconds = 0.0

    for line in script.lines:
        scene_voice = _resolve_scene_voice(voice_name, casting_by_scene, line.scene_index, format)
        scene_audio_file = os.path.join(task_directory, f"audio_scene_{line.scene_index}.mp3")
        scene_subtitle_file = os.path.join(
            task_directory, f"subtitle_scene_{line.scene_index}.srt"
        )

        sub_maker = voice.tts(
            text=line.text,
            voice_name=voice.parse_voice_name(scene_voice),
            voice_rate=voice_rate,
            voice_file=scene_audio_file,
            voice_volume=voice_volume,
        )
        if sub_maker is None:
            raise RuntimeError(
                f"failed to synthesize narration audio for scene {line.scene_index}; "
                "check the selected voice and TTS connectivity"
            )

        voice.create_subtitle(sub_maker, line.text, scene_subtitle_file)
        scene_subtitle_files.append((scene_subtitle_file, cumulative_seconds))
        scene_temp_files.append(scene_audio_file)
        scene_temp_files.append(scene_subtitle_file)

        scene_segment = AudioSegment.from_file(scene_audio_file)
        combined_audio += scene_segment
        cumulative_seconds += len(scene_segment) / 1000.0

    combined_audio.export(audio_file, format="mp3")
    subtitle_written = voice.merge_scene_subtitles(scene_subtitle_files, subtitle_file)

    for temp_file in scene_temp_files:
        try:
            os.remove(temp_file)
        except OSError:
            pass

    return AudioTrack(
        voice_name=voice_name,
        voice_file=audio_file,
        subtitle_file=subtitle_file if subtitle_written else "",
        duration_seconds=cumulative_seconds,
    )


def _resolve_narration_voice(
    voice_name: str, character_references: list[CharacterReference] | None
) -> str:
    """"Karakter Sesi" planı (kullanıcı onaylı, Seçenek A): tam olarak TEK
    bir karakter seçiliyken, anlatım kullanıcının seçtiği genel ses yerine
    O KARAKTERİN kayıtlı sesiyle okunur -- TTS çağrısı hâlâ TEK, script
    şeması hiç değişmiyor, sadece hangi voice_name kullanıldığı.

    Çoklu-karakter sahneler (ör. "Anne Kuş & Yavrusu", character_
    references'ta 2+ eleman) BİLİNÇLİ OLARAK kapsam dışı -- kullanıcının
    kendi kararı: hangi karakterin sesinin kullanılacağı belirsiz
    (Seçenek B'nin, gerçek diyalog turunun konusu), bu yüzden burada
    davranış HİÇ değişmiyor, mevcut/genel voice_name aynen kullanılıyor.

    Karakter seçili değilse (`character_references` boş/None) ya da
    eşleşen bir kayıt bulunamazsa (`""` dönerse) da davranış hiç
    değişmiyor -- regresyon garantisi.
    """
    if character_references and len(character_references) == 1:
        character_voice = characters.get_voice_name_for_character_reference(
            character_references[0]
        )
        if character_voice:
            return character_voice
    return voice_name


def _should_use_per_scene_narration(
    casting_by_scene: dict[int, dict] | None, format: Format | None
) -> bool:
    """Per-scene rendering (N separate TTS calls) is only worth its extra
    cost/latency when it can actually produce a DIFFERENT result than the
    single-call path for at least one scene:

    - any scene has 1+ cast characters (their own voice would differ from
      the general voice_name), OR
    - format is Kids (the "no character assigned" fallback -- Professor
      Nova instead of the general voice_name -- can apply even when NO
      scene has a cast character at all).

    `casting_by_scene` being falsy (Auto character casting never ran --
    character_selection != AUTO_CHARACTER) always short-circuits to False,
    REGARDLESS of format -- this is the regression guarantee: fixed/no-
    character projects (Kids or not) are never touched by this function.
    """
    if not casting_by_scene:
        return False
    if format == Format.kids:
        return True
    return any((entry or {}).get("characters") for entry in casting_by_scene.values())


def render_audio_plan(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    bgm_file: str = "",
    character_references: list[CharacterReference] | None = None,
    casting_by_scene: dict[int, dict] | None = None,
    format: Format | None = None,
) -> AudioPlan:
    """"Sahne Bazlı Gerçek Ses Değişimi" planı (kullanıcı onaylı): Auto
    kadrolama gerçekten devredeyken (bkz. _should_use_per_scene_narration),
    render_narration_by_scene()'in sahne bazlı çoklu-ses yoluna dallanır --
    her diğer durumda davranış ESKİSİYLE BİREBİR AYNI kalır:
    _resolve_narration_voice() + tek çağrılı render_narration(). İki
    mekanizma (_resolve_narration_voice'un tek sabit karakter override'ı ile
    bu sahne-bazlı yol) birbirini ASLA tetiklemez -- Auto modda zaten
    `character_references` (sabit liste) boş geliyor, non-Auto modda ise
    `casting_by_scene` hiç üretilmiyor (character_selection ==
    AUTO_CHARACTER DEĞİLSE default_pipeline bu parametreyi hiç doldurmaz).
    """
    if _should_use_per_scene_narration(casting_by_scene, format):
        narration = render_narration_by_scene(
            script, task_id, voice_name, casting_by_scene, voice_rate, voice_volume, format
        )
    else:
        resolved_voice_name = _resolve_narration_voice(voice_name, character_references)
        narration = render_narration(
            script, task_id, resolved_voice_name, voice_rate, voice_volume
        )
    return AudioPlan(narration=narration, bgm_file=bgm_file)
