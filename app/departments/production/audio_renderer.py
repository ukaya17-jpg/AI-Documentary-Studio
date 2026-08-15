"""Audio (TTS) stage: synthesize narration and a matching subtitle file.

Thin wrapper around the legacy app.services.voice tts()/create_subtitle(),
reused as-is, not reimplemented.
"""

import os

from app.config import characters
from app.models.audio import AudioPlan, AudioTrack
from app.models.character import CharacterReference
from app.models.script import Script
from app.services import voice
from app.utils import utils


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


def _resolve_scene_voice(
    voice_name: str, casting_by_scene: dict[int, dict] | None, scene_index: int
) -> str:
    """"Sahne Bazlı Gerçek Ses Değişimi" planı (kullanıcı onaylı): Auto
    kadrolamanın bu sahne için seçtiği karakterin (varsa) kendi kayıtlı
    sesini döndürür -- yoksa (karaktersiz sahne, ya da slug artık registry'de
    yoksa) genel `voice_name`'e düşer. `_resolve_narration_voice()`'ın
    (tek, proje-geneli karakter) DEĞİL, sahne bazlı `casting_by_scene`'in
    üzerinde çalışır -- ikisi paralel, birbirinden bağımsız mekanizmalar.
    """
    character_slug = (casting_by_scene or {}).get(scene_index, {}).get("character")
    if character_slug:
        try:
            return characters.get_character_voice_name(character_slug)
        except KeyError:
            pass
    return voice_name


def render_narration_by_scene(
    script: Script,
    task_id: str,
    voice_name: str,
    casting_by_scene: dict[int, dict],
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
) -> AudioTrack:
    """Same external contract as render_narration() (one AudioTrack covering
    the WHOLE script), but synthesizes each script.lines[i] SEPARATELY,
    using that scene's Auto-cast character's own registered voice where one
    was picked (casting_by_scene, from casting_generator's per-scene
    decision), falling back to `voice_name` otherwise -- then concatenates
    the per-scene audio into one continuous audio.mp3 and merges the
    per-scene subtitle cues (each anchored to that scene's own real,
    measured TTS duration) into one subtitle.srt via
    voice.merge_scene_subtitles().

    Only called by render_audio_plan() when Auto-mode casting actually
    picked at least one character for at least one scene -- every other
    case (no casting, Auto picked none, non-Auto fixed/no character) keeps
    using the original single-call render_narration(), so those projects
    are byte-for-byte unaffected by this function's existence.
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
        scene_voice = _resolve_scene_voice(voice_name, casting_by_scene, line.scene_index)
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


def _casting_by_scene_has_a_character(casting_by_scene: dict[int, dict] | None) -> bool:
    return bool(casting_by_scene) and any(
        (entry or {}).get("character") for entry in casting_by_scene.values()
    )


def render_audio_plan(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    bgm_file: str = "",
    character_references: list[CharacterReference] | None = None,
    casting_by_scene: dict[int, dict] | None = None,
) -> AudioPlan:
    """"Sahne Bazlı Gerçek Ses Değişimi" planı (kullanıcı onaylı): Auto
    kadrolamanın en az bir sahne için gerçekten bir karakter seçtiği
    durumda (`casting_by_scene`), render_narration_by_scene()'in sahne
    bazlı çoklu-ses yoluna dallanır -- her diğer durumda (casting_by_scene
    boş/None, ya da Auto hiçbir sahnede karakter seçmemişse) davranış
    ESKİSİYLE BİREBİR AYNI kalır: _resolve_narration_voice() + tek çağrılı
    render_narration(). İki mekanizma (_resolve_narration_voice'un tek
    sabit karakter override'ı ile bu sahne-bazlı yol) birbirini ASLA
    tetiklemez -- Auto modda zaten `character_references` (sabit liste)
    boş geliyor, non-Auto modda ise `casting_by_scene` hiç üretilmiyor.
    """
    if _casting_by_scene_has_a_character(casting_by_scene):
        narration = render_narration_by_scene(
            script, task_id, voice_name, casting_by_scene, voice_rate, voice_volume
        )
    else:
        resolved_voice_name = _resolve_narration_voice(voice_name, character_references)
        narration = render_narration(
            script, task_id, resolved_voice_name, voice_rate, voice_volume
        )
    return AudioPlan(narration=narration, bgm_file=bgm_file)
