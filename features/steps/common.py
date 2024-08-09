from behave import given, when, then, step


@given('user is authenticated')
def step_impl(context):
    assert True


@when('user visits the "{path}" page')
def step_impl(context, path):
    context.browser.get(f"http://localhost:8000{path}")


@when('user reloads the "{path}" page')
def step_impl(context, path):
    context.execute_steps(f'when user visits the "{path}" page')
