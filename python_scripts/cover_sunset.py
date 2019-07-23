"""Manages roller shutters sunset routine"""

presence = hass.states.get('group.family')
logger.debug("Family presence status is \"{}\"".format(presence))
if presence is 'home':
    hass.services.call(domain="python_script",
                       service="cover_mode",
                       service_data={"mode": "sera"})
else:
    # even on "unknown" state
    hass.services.call(domain="cover",
                       service="close_cover",
                       service_data={"entity_id": "all"})
