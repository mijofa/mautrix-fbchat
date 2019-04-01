#!/usr/bin/python3
import getpass
import secrets

import yaml

import fbchat


appservice_port = 8091  # FIXME: Make this more dynamic, or at least configurable with a command-line argument


fb_username = input("Facebook username, email address, or phone number: ")
fb_password = getpass.getpass("Facebook password (will not echo): ")
print("Logging into Facebook now.  If prompted for 2FA code, you can give an empty code if you accept the notification prompts from a logged in session")
fb = fbchat.Client(
    email=fb_username,
    password=fb_password)


registration_data = {
    'id': f"fbchat bridge for {fb.uid}",
    'url': f"http://127.0.0.1:{appservice_port}",  # FIXME: Is this actually needed?
    'hs_token': secrets.token_hex(),  # Does this follow the same spec as Matrix expects?
    'as_token': secrets.token_hex(),  # Perhaps it could be more random?
    'namespaces': {
        # Yes these are single-item lists, it's not a typo, Synapse actually needs it to work that way.
        'users': [{
            'exclusive': True,
            'regex': f"@fbchat_{fb.uid}_*",
        }],
        'aliases': [{
            'exclusive': True,
            'regex': f"#fbchat_{fb.uid}_*",
        }],
        'rooms': []  # FIXME: Can I get away with just removing this?
    },
    'sender_localpart': f"fbchat_{fb.uid}",
    'rate_limited': True,  # FIXME: Facebook does rate limiting internally, but good to have this in case I fuck up the Python code
    'protocols': ["fbchat"],

    # I would like to avoid having multiple config files sharing some of the same secret tokens.
    # So instead of copying the as/hs_token values into another config file along with the Facebook auth tokens,
    # I'm just going include the Facebook auth tokens in with the Synapse config and rely on Synapse ignoring it.
    'fbchat_session': fb.getSession(),  # FIXME: Do I need the whole thing? Is this secure enough?
}
with open(f"fbchat_{fb.uid}_appservice.yaml", 'w') as f:
    yaml.dump(registration_data, f)

print(f"\n\nNow Copy {f.name} into a more sensible place and append it to Synapse's app_service_config_files option in homeserver.yaml\n")
