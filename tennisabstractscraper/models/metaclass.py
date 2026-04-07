"""
By default, classes are constructed using type(). The class body is executed in 
a new namespace and the class name is bound locally to the result of type(name, bases, namespace).

The class creation process can be customized by passing the metaclass keyword argument in the class 
definition line, or by inheriting from an existing class that included such an argument. In the following example, 
both MyClass and MySubclass are instances of Meta:

Meta (metaclass)
│
├── MyClass  (instance of Meta)
│    │
│    └── MySubclass (instance of Meta)
----------------------------------------------
                    Meta 
                 (metaclass)
                      │
                      │ <-- type of MyClass
         ┌────────────┴────────────┐
         │                         │
      MyClass                 MySubclass
(instance of meta)        (instance of meta)
         │                         │
         └─────────────────────>  obj
                      (instance of MySubclass)



Any other keyword arguments that are specified in the class definition are passed through to all metaclass operations described below.

When a class definition is executed, the following steps occur:
- MRO entries are resolved;
- the appropriate metaclass is determined;
- the class namespace is prepared;
- the class body is executed;
- the class object is created.
"""

class Meta(type):
  """
  It controls how MyClass and MySubclass are created.
  """
  def __new__(cls, name, bases, dct):
        dct['meta_attr'] = f"I am in {name}"
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=Meta):
  """
  It is an instance of Meta. To check:

  >>> type(MyClass)
  <class '__main__.Meta'>
  
  """
  pass

class MySubclass(MyClass):
  """
  Since it inherits from MyClass (which uses Meta), it automatically uses Meta as its metaclass.
  To check:

  >>> type(MySubclass)
  <class '__main__.Meta'>

  """
  pass

print(MyClass.meta_attr)      # Output: I am in MyClass
print(MySubclass.meta_attr)   # Output: I am in MySubclass