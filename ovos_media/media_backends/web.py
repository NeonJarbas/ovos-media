from ovos_bus_client.message import Message
from ovos_utils.log import LOG

from ovos_plugin_manager.ocp import find_ocp_web_plugins
from ovos_plugin_manager.templates.media import RemoteWebPlayerBackend
from .base import BaseMediaService


class WebService(BaseMediaService):
    """ Web Service class.
        Handles playback of web and selecting proper backend for the uri
        to be played.
    """

    def load_services(self):
        """Method for loading services.

        Sets up the global service, default and registers the event handlers
        for the subsystem.
        """

        local = []
        remote = []

        plugs = find_ocp_web_plugins()
        for plug_name, plug_cfg in self.config.get("web_players", {}).items():
            plug_name = plug_cfg["module"]
            try:
                service = plugs[plug_name](plug_cfg, self.bus)
                if isinstance(service, RemoteWebPlayerBackend):
                    remote.append(service)
                else:
                    local.append(service)
            except:
                LOG.exception(f"Failed to load {plug_name}")

            # Sort services so local services are checked first
        self.services = local + remote

        # Register end of track callback
        for s in self.services:
            s.set_track_start_callback(self.track_start)

        # Setup event handlers
        self.bus.on('ovos.web.service.play', self._play)
        self.bus.on('ovos.web.service.pause', self._pause)
        self.bus.on('ovos.web.service.resume', self._resume)
        self.bus.on('ovos.web.service.stop', self._stop)
        self.bus.on('ovos.web.service.track_info', self._track_info)
        self.bus.on('ovos.web.service.list_backends', self._list_backends)
        self.bus.on('ovos.web.service.set_track_position', self._set_track_position)
        self.bus.on('ovos.web.service.get_track_position', self._get_track_position)
        self.bus.on('ovos.web.service.get_track_length', self._get_track_length)
        self.bus.on('ovos.web.service.seek_forward', self._seek_forward)
        self.bus.on('ovos.web.service.seek_backward', self._seek_backward)
        self.bus.on('ovos.web.service.duck', self._lower_volume)
        self.bus.on('ovos.web.service.unduck', self._restore_volume)

        self._loaded.set()  # Report services loaded

        return self.services

    def track_start(self, track):
        """Callback method called from the services to indicate start of
        playback of a track or end of playlist.
        """
        if track:
            # Inform about the track about to start.
            LOG.debug('New track coming up!')
            self.bus.emit(Message('ovos.web.playing_track',
                                  data={'track': track}))
        else:
            # If no track is about to start last track of the queue has been
            # played.
            LOG.debug('End of playlist!')
            self.bus.emit(Message('ovos.web.queue_end'))

    def remove_listeners(self):
        self.bus.remove('ovos.web.service.play', self._play)
        self.bus.remove('ovos.web.service.pause', self._pause)
        self.bus.remove('ovos.web.service.resume', self._resume)
        self.bus.remove('ovos.web.service.stop', self._stop)
        self.bus.remove('ovos.web.service.track_info', self._track_info)
        self.bus.remove('ovos.web.service.get_track_position', self._get_track_position)
        self.bus.remove('ovos.web.service.set_track_position', self._set_track_position)
        self.bus.remove('ovos.web.service.get_track_length', self._get_track_length)
        self.bus.remove('ovos.web.service.seek_forward', self._seek_forward)
        self.bus.remove('ovos.web.service.seek_backward', self._seek_backward)
