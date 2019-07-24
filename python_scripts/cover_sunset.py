"""Manages roller shutters sunset routine"""

presence = hass.states.get('group.family')
if presence is not None:
    current_state = presence.state
    logger.info("Family presence status is \"{}\"".format(current_state))
    if current_state is 'home':
        hass.services.call(domain="python_script",
                           service="cover_mode",
                           service_data={"mode": "sera"})
    else:
        # even on "unknown" state
        hass.services.call(domain="cover",
                           service="close_cover",
                           service_data={"entity_id": "all"})
