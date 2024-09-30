from exception_handler.notifiers.base_notifier import BaseNotifier

class SentryNotifier(BaseNotifier):
    def process_exception(self, payload):
        event = payload.get('data', {}).get('event', {})
        exception = event.get('exception', {}).get('values', [{}])[0]
        return {
            "event_id": event.get('event_id'),
            "project": event.get('project'),
            "environment": event.get('environment'),
            "platform": event.get('platform'),
            "release": event.get('release'),
            "transaction": event.get('transaction'),
            "exception": {
                "type": exception.get('type'),
                "value": exception.get('value'),
                "module": exception.get('module'),
            },
            "stacktrace": [frame for frame in exception.get('stacktrace', {}).get('frames', []) if frame.get('in_app')],
            "context": {
                "request": event.get('request', {}),
                "user": event.get('user', {}),
            },
            "tags": dict(event.get('tags', [])),
            "extra": event.get('extra', {}),
            "timestamp": event.get('timestamp'),
            "url": event.get('url'),
            "issue_id": event.get('issue_id'),
            "web_url": event.get('web_url')
        }