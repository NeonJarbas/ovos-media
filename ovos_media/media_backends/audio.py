from ovos_bus_client.message import Message
from ovos_utils.log import LOG

from ovos_config.config import Configuration
from ovos_media.media_backends.base import BaseMediaService
from ovos_plugin_manager.ocp import find_ocp_audio_plugins
from ovos_plugin_manager.templates.media import RemoteAudioPlayerBackend


class AudioService(BaseMediaService):
    """ Audio Service class.
        Handles playback of audio and selecting proper backend for the uri
        to be played.
    """

    def __init__(self, bus, config=None, autoload=True, validate_source=True):
        """
            Args:
                bus: Mycroft messagebus
        """
        config = config or Configuration().get("media") or {}
        super().__init__(bus, config, autoload, validate_source)

    def _get_preferred_audio_backend(self):
        """
        Check configuration and available backends to select a preferred backend

        """
        available = []
        preferred = self.config.get("preferred_audio_services") or \
                    ["vlc", "mplayer", "cli"]
        for b in preferred:
            if b in available:
                return b
        LOG.error("Preferred audio service backend not installed")
        return "simple"

    def load_services(self):
        """Method for loading services.

        Sets up the global service, default and registers the event handlers
        for the subsystem.
        """
        local = []
        remote = []

        plugs = find_ocp_audio_plugins()
        for plug_name, plug_cfg in self.config.get("audio_players", {}).items():
            try:
                service = plugs[plug_name](plug_cfg, self.bus)
                if isinstance(service, RemoteAudioPlayerBackend):
                    remote += service
                else:
                    local += service
            except:
                LOG.exception(f"Failed to load {plug_name}")

        # Sort services so local services are checked first
        self.service = local + remote

        # Register end of track callback
        for s in self.service:
            s.set_track_start_callback(self.track_start)

        LOG.info('Finding default audio backend...')
        self.default = self._get_preferred_audio_backend()

        # Setup event handlers
        self.bus.on('ovos.audio.service.play', self._play)
        self.bus.on('ovos.audio.service.pause', self._pause)
        self.bus.on('ovos.audio.service.resume', self._resume)
        self.bus.on('ovos.audio.service.stop', self._stop)
        self.bus.on('ovos.audio.service.track_info', self._track_info)
        self.bus.on('ovos.audio.service.list_backends', self._list_backends)
        self.bus.on('ovos.audio.service.set_track_position', self._set_track_position)
        self.bus.on('ovos.audio.service.get_track_position', self._get_track_position)
        self.bus.on('ovos.audio.service.get_track_length', self._get_track_length)
        self.bus.on('ovos.audio.service.seek_forward', self._seek_forward)
        self.bus.on('ovos.audio.service.seek_backward', self._seek_backward)
        self.bus.on('ovos.audio.service.duck', self._lower_volume)
        self.bus.on('ovos.audio.service.unduck', self._restore_volume)

        self._loaded.set()  # Report services loaded
        return self.service

    def track_start(self, track):
        """Callback method called from the services to indicate start of
        playback of a track or end of playlist.
        """
        if track:
            # Inform about the track about to start.
            LOG.debug('New track coming up!')
            self.bus.emit(Message('mycroft.audio.playing_track',
                                  data={'track': track}))
        else:
            # If no track is about to start last track of the queue has been
            # played.
            LOG.debug('End of playlist!')
            self.bus.emit(Message('mycroft.audio.queue_end'))

    def remove_listeners(self):
        self.bus.remove('ovos.audio.service.play', self._play)
        self.bus.remove('ovos.audio.service.pause', self._pause)
        self.bus.remove('ovos.audio.service.resume', self._resume)
        self.bus.remove('ovos.audio.service.stop', self._stop)
        self.bus.remove('ovos.audio.service.track_info', self._track_info)
        self.bus.remove('ovos.audio.service.get_track_position', self._get_track_position)
        self.bus.remove('ovos.audio.service.set_track_position', self._set_track_position)
        self.bus.remove('ovos.audio.service.get_track_length', self._get_track_length)
        self.bus.remove('ovos.audio.service.seek_forward', self._seek_forward)
        self.bus.remove('ovos.audio.service.seek_backward', self._seek_backward)
