"""Manages roller shutters sunset routine"""

presence = hass.states.get('group.all_devices')
logger.debug("devices presence status is \"{}\"".format(presence))
if presence is 'home':
    hass.services.async_call(domain="python_script",
                             service="cover_mode",
                             service_data={"mode": "sera"})
else:
    # even on "unknown" state
    hass.services.async_call(domain="cover",
                             service="close_cover")
