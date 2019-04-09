from sfa_dash.api_interface import get_request, post_request


def get_metadata(observation_id):
    r = get_request(f'/observations/{observation_id}/metadata')
    return r


def get_values(observation_id, **kwargs):
    r = get_request(f'/observations/{observation_id}/values', **kwargs)
    return r


def list_metadata(site_id=None):
    if site_id is not None:
        r = get_request(f'/sites/{site_id}/observations')
    else:
        r = get_request('/observations/')
    return r


def post_metadata(obs_dict):
    r = post_request('/observations/', obs_dict)
    return r


def post_values(uuid, values, json=True):
    r = post_request(f'/observations/{uuid}/values', values, json)
    return r