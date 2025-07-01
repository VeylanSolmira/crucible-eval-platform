hasattr() in Python: A Quick Guide

  What is hasattr()?

  hasattr(object, name) checks if an object has
  an attribute with the given name. It returns
  True if the attribute exists, False otherwise.

  class Person:
      def __init__(self):
          self.name = "Alice"

  person = Person()
  print(hasattr(person, 'name'))  # True
  print(hasattr(person, 'age'))   # False

  When to Use hasattr()

  ✅ Good Use Cases:

  1. Duck Typing / Protocol Checking
  def process_data(obj):
      if hasattr(obj, 'read') and hasattr(obj,
  'write'):
          # It's file-like, we can use it
          data = obj.read()
          obj.write(processed_data)

  2. Optional Attributes in External APIs
  # When working with responses that might vary
  if hasattr(response, 'headers'):
      content_type =
  response.headers.get('Content-Type')

  3. Backwards Compatibility
  # Check if newer API features exist
  if hasattr(library, 'new_feature'):
      library.new_feature()
  else:
      # Fall back to old method
      library.old_method()

  4. Dynamic Attribute Access
  def get_config_value(config_obj, key, 
  default=None):
      if hasattr(config_obj, key):
          return getattr(config_obj, key)
      return default

  When NOT to Use hasattr()

  ❌ Anti-patterns:

  1. Instead of Try/Except (EAFP)
  # Bad - LBYL (Look Before You Leap)
  if hasattr(obj, 'method'):
      obj.method()

  # Better - EAFP (Easier to Ask Forgiveness 
  than Permission)
  try:
      obj.method()
  except AttributeError:
      # Handle missing method
      pass

  2. For Your Own Classes
  # Bad - You control this class!
  class MyClass:
      def process(self):
          if hasattr(self, 'data'):
              return self.data

  # Better - Initialize properly
  class MyClass:
      def __init__(self):
          self.data = None

      def process(self):
          return self.data

  3. Performance-Critical Code
  # hasattr() can be slow in tight loops
  # Bad
  for item in million_items:
      if hasattr(item, 'process'):
          item.process()

  # Better - assume protocol or use try/except
  for item in million_items:
      try:
          item.process()
      except AttributeError:
          continue

  The Hidden Gotcha

  hasattr() actually calls getattr() internally
  and catches exceptions. This means:

  class Tricky:
      @property
      def explosive(self):
          raise Exception("BOOM!")

  obj = Tricky()
  # This will return False, swallowing the 
  exception!
  print(hasattr(obj, 'explosive'))  # False, not
   an exception!

  Best Practices

  1. Use for External/Unknown Objects: Great for
   APIs, libraries, or user-provided objects
  2. Prefer Try/Except for Known Code: More
  Pythonic and often faster
  3. Document Why: When you use hasattr(),
  comment why the attribute might be missing
  4. Consider getattr() with Default: Sometimes
  getattr(obj, 'attr', default) is cleaner

  In Our Celery Code

  # Good use - checking if exception has 
  optional response attribute
  if hasattr(e, 'response') and e.response:
      status_code = e.response.status_code

  This is appropriate because:
  - We're dealing with external library
  exceptions (httpx)
  - The response attribute is optional depending
   on error type
  - We need to safely check before accessing
  status_code