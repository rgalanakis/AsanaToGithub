import datetime
import json


class TaskCache(object):
    def __init__(self, use_cache, cache_path):
        self.use_cache = use_cache
        self.cache_path = cache_path or '.asanagh.cache'

    def load(self):
        if not self.use_cache:
            return {}
        try:
            with open(self.cache_path) as f:
                return json.load(f)
        except (IOError, ValueError):
            return {}

    def save(self, cache):
        if not self.use_cache:
            return
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=2)

    def includes(self, task):
        cache = self.load()
        return str(task['id']) in cache

    def set(self, task):
        cache = self.load()
        cache[task['id']] = {
            'name': task['name'],
            'copied_at': datetime.datetime.now().isoformat(),
            'completed_state': task['completed']
        }
        self.save(cache)
