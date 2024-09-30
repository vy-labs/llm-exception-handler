from exception_handler.notifiers.sentry_notifier import SentryNotifier

def get_notifier(config, notifier_type):
    if notifier_type.lower() == 'sentry':
        return SentryNotifier(config)
    else:
        raise ValueError(f"Unsupported notifier type: {notifier_type}")