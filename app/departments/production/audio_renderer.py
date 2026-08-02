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


def render_audio_plan(
    script: Script,
    task_id: str,
    voice_name: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    bgm_file: str = "",
    character_references: list[CharacterReference] | None = None,
) -> AudioPlan:
    resolved_voice_name = _resolve_narration_voice(voice_name, character_references)
    narration = render_narration(script, task_id, resolved_voice_name, voice_rate, voice_volume)
    return AudioPlan(narration=narration, bgm_file=bgm_file)
