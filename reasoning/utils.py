

def make_prompt_factory(role, content):
    return {"role": f"{role}", "content": f"{content}"}


def make_system(content):
    return make_prompt_factory('system', content)


def make_user(content):
    return make_prompt_factory('user', content)


def make_assistant(content):
    return make_prompt_factory('assistant', content)


def make_script(action: str):
    return action
