from .capture import AudioCapture, AudioCaptureConfig
<<<<<<< HEAD
from .playback import AudioPlayback, AudioPlaybackConfig
from .vad import VoiceActivityDetector, VadConfig, VadState
=======
from .vad import VoiceActivityDetector, VadConfig, VadState

try:
    from .playback import AudioPlayback, AudioPlaybackConfig
except ImportError:
    pass

try:
    from src.config.settings import NexusConfig
except ImportError:
    pass
>>>>>>> febf6a8 (feat(ui): add NexusConfig and settings panel (ARCH-009))
