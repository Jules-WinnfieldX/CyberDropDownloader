from typing import Dict

import browser_cookie3

from cyberdrop_dl.managers.manager import Manager


# noinspection PyProtectedMember
def get_forum_cookies(manager: Manager, browser: str) -> None:
    """Get the cookies for the forums"""
    auth_args: Dict = manager.config_manager.authentication_data

    if browser == 'chrome':
        nudostar = browser_cookie3.chrome(domain_name='nudostar.com')
        simpcity = browser_cookie3.chrome(domain_name='simpcity.su')
        socialmediagirls = browser_cookie3.chrome(domain_name='forums.socialmediagirls.com')
        xbunker = browser_cookie3.chrome(domain_name='xbunker.nu')
    elif browser == 'firefox':
        nudostar = browser_cookie3.firefox(domain_name='nudostar.com')
        simpcity = browser_cookie3.firefox(domain_name='simpcity.su')
        socialmediagirls = browser_cookie3.firefox(domain_name='forums.socialmediagirls.com')
        xbunker = browser_cookie3.firefox(domain_name='xbunker.nu')
    elif browser == 'edge':
        nudostar = browser_cookie3.edge(domain_name='nudostar.com')
        simpcity = browser_cookie3.edge(domain_name='simpcity.su')
        socialmediagirls = browser_cookie3.edge(domain_name='forums.socialmediagirls.com')
        xbunker = browser_cookie3.edge(domain_name='xbunker.nu')
    elif browser == 'safari':
        nudostar = browser_cookie3.safari(domain_name='nudostar.com')
        simpcity = browser_cookie3.safari(domain_name='simpcity.su')
        socialmediagirls = browser_cookie3.safari(domain_name='forums.socialmediagirls.com')
        xbunker = browser_cookie3.safari(domain_name='xbunker.nu')
    elif browser == 'opera':
        nudostar = browser_cookie3.opera(domain_name="nudostar.com")
        simpcity = browser_cookie3.opera(domain_name="simpcity.su")
        socialmediagirls = browser_cookie3.opera(domain_name="forums.socialmediagirls.com")
        xbunker = browser_cookie3.opera(domain_name="xbunker.nu")
    elif browser == 'brave':
        nudostar = browser_cookie3.brave(domain_name="nudostar.com")
        simpcity = browser_cookie3.brave(domain_name="simpcity.su")
        socialmediagirls = browser_cookie3.brave(domain_name="forums.socialmediagirls.com")
        xbunker = browser_cookie3.brave(domain_name="xbunker.nu")
    else:
        raise ValueError('Invalid browser specified')

    try:
        auth_args['Forums']['nudostar_xf_user_cookie'] = nudostar._cookies['nudostar.com']['/']['xf_user'].value
    except KeyError:
        pass
    try:
        auth_args['Forums']['simpcity_xf_user_cookie'] = simpcity._cookies['simpcity.su']['/']['xf_user'].value
    except KeyError:
        pass
    try:
        auth_args['Forums']['socialmediagirls_xf_user_cookie'] = socialmediagirls._cookies['forums.socialmediagirls.com']['/']['xf_user'].value
    except KeyError:
        pass
    try:
        auth_args['Forums']['xbunker_xf_user_cookie'] = xbunker._cookies['xbunker.nu']['/']['xf_user'].value
    except KeyError:
        pass

    manager.cache_manager.save("browser", browser)
