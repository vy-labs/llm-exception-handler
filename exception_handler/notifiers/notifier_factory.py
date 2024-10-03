from exception_handler.notifiers.sentry_notifier import SentryNotifier

def get_notifier(config):
    notifier_type = config.get('notifier', '').lower()
    if notifier_type == 'sentry':
        return SentryNotifier(config)
    else:
        raise ValueError(f"Unsupported notifier type: {notifier_type}")