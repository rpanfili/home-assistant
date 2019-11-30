"""Manages covers scene"""


def get_window_id_by_cover_id(entity_id):
    return entity_id.replace("cover", "binary_sensor") + "_window"


def is_window_opened(entity_id, hass, logger):
    opened = True
    window = hass.states.get(entity_id)
    if window is not None:
        opened = window.state is 'on'
    else:
        logger.warning("Window \"{}\" does not exists. Assume default state: {}".format(
            window_id,
            'opened' if opened else 'not opened'))
    return opened


mode = data.get('mode', None)

cover_conf = {}

if mode is None:
    logger.error("Missing \"mode\" parameter! Abort..")

elif mode == 'sera':
    cover_conf = {
        'cover.bathroom':          25,
        'cover.bedroom':           40,
        'cover.green_room':        25,
        'cover.kitchen_left':      50,
        'cover.kitchen_right':     85,
        'cover.living_room_left':  25,
        'cover.living_room_right': 70,
        'cover.pink_room':         25,
    }

elif mode in ['afa', 'caldo']:
    cover_conf = {
        'cover.bathroom':          100,
        'cover.bedroom':           40,
        'cover.green_room':        70,
        'cover.kitchen_left':      40,
        'cover.kitchen_right':     50,
        'cover.living_room_left':  25,
        'cover.living_room_right': 50,
        'cover.pink_room':         40,
    }

elif mode in ['notte estiva']:
    cover_conf = {
        'cover.bathroom':          25,
        'cover.bedroom':           75,
        'cover.green_room':        25,
        'cover.kitchen_left':      25,
        'cover.kitchen_right':     25,
        'cover.living_room_left':  0,
        'cover.living_room_right': 25,
        'cover.pink_room':         25,
    }
elif mode in ['notte invernale', 'notte']:
    cover_conf = {
        'cover.bathroom':          0,
        'cover.bedroom':           10,
        'cover.green_room':        0,
        'cover.kitchen_left':      0,
        'cover.kitchen_right':     0,
        'cover.living_room_left':  0,
        'cover.living_room_right': 0,
        'cover.pink_room':         0,
    }
elif mode in ['fuori casa']:
    balcony = hass.states.get('group.roller_shutters_with_balcony')
    if balcony is not None:
        for entity_id in balcony.attributes.get('entity_id'):
            window_id = get_window_id_by_cover_id(entity_id)
            if is_window_opened(window_id, hass, logger):
                logger.debug(
                    "{} window is opened, close its cover".format(window_id))
                hass.services.call(domain="cover",
                                   service="close_cover",
                                   service_data={"entity_id": entity_id})


else:
    logger.warning("Unknown mode \"{}\"".format(mode))
    hass.services.call(domain="tts",
                       service="google_translate_say",
                       service_data={
                           'entity_id': 'media_player.kitchen_speaker',
                           "message": "Siamo spiacenti ma la signora {} non è in casa! La preghiamo di riprovare più tardi".format(mode),
                           "language": "it"
                       })


if cover_conf:
    logger.info("Cover mode to \"{}\"".format(mode))

    for entity_id, position in cover_conf.items():
        hass.services.call('cover', 'set_cover_position', {
            'entity_id': entity_id,
            'position': position
        }, False)

    logger.debug("Done")
