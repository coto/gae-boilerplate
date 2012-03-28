"""Tests for polymodel.py.

See issue 35.  http://goo.gl/iHkCm
"""

import pickle
import unittest

from .google_imports import namespace_manager
from .google_imports import datastore_types

from . import polymodel
from . import model
from . import test_utils


PolyModel = polymodel.PolyModel


class PolyModelTests(test_utils.NDBTest):

  def setUp(self):
    super(PolyModelTests, self).setUp()

  the_module = polymodel

  def testBasics(self):
    # Test basic PolyModel functionality.
    class Shoe(PolyModel):
      color = model.StringProperty()
    class Moccasin(Shoe):
      leather = model.StringProperty()
    class Sneaker(Shoe):
      pump = model.BooleanProperty()

    self.assertEqual(Shoe._class_name(), 'Shoe')
    self.assertEqual(Shoe._class_key(), ['Shoe'])
    self.assertEqual(Moccasin._class_name(), 'Moccasin')
    self.assertEqual(Moccasin._class_key(), ['Shoe', 'Moccasin'])
    self.assertEqual(Sneaker._class_name(), 'Sneaker')
    self.assertEqual(Sneaker._class_key(), ['Shoe', 'Sneaker'])

    s_key = model.Key('Shoe', 1)
    self.assertEqual(Shoe().put(), s_key)
    s = s_key.get()
    self.assertEqual(s._get_kind(), 'Shoe')
    self.assertEqual(s._class_key(), ['Shoe'])
    self.assertEqual(s.class_, ['Shoe'])

    m_key = model.Key('Shoe', 2)
    self.assertEqual(Moccasin(color='brown', leather='cattlehide').put(),
                     m_key)
    m = m_key.get()
    self.assertEqual(m._get_kind(), 'Shoe')
    self.assertEqual(m.class_, ['Shoe', 'Moccasin'])

    snkr_key = model.Key('Shoe', 3)
    self.assertEqual(Sneaker(color='red', pump=False).put(), snkr_key)
    snkr = snkr_key.get()
    self.assertEqual(snkr._get_kind(), 'Shoe')
    self.assertEqual(snkr.class_, ['Shoe', 'Sneaker'])

    self.assertEqual(Shoe.query().fetch(), [s, m, snkr])
    self.assertEqual(Shoe.query(Sneaker.pump == False).fetch(), [snkr])
    self.assertEqual(Moccasin.query().fetch(), [m])
    self.assertEqual(Sneaker.query().fetch(), [snkr])

  def testBlobKeyProperty(self):
    class MyModel(PolyModel):
      pass
    class MyDerivedModel(MyModel):
      image = model.BlobKeyProperty()

    test_blobkey = datastore_types.BlobKey('testkey123')
    m = MyDerivedModel()
    m.image = test_blobkey
    m.put()

    m = m.key.get()
    m.image = test_blobkey
    m.put()

    self.assertTrue(isinstance(m.image, datastore_types.BlobKey))
    self.assertEqual(str(m.image), str(test_blobkey))

  def testClassKeyProperty(self):
    # Tests for the class_ property.
    class Animal(PolyModel):
      pass
    class Dog(Animal):
      pass
    fido = Dog()
    self.assertEqual(fido.class_, ['Animal', 'Dog'])
    self.assertRaises(TypeError, setattr, fido, 'class_', ['Animal', 'Dog'])

  def testPolyExpando(self):
    # Test that PolyModel can be combined with Expando.
    # (See also testExpandoPoly, and the Ghoul class in testInheritance.)
    class Animal(PolyModel, model.Expando):
      pass
    class Mammal(Animal):
      pass
    cat = Mammal(name='Tom', naps=18, sound='purr')
    cat1 = cat.put().get()
    self.assertFalse(cat1 is cat)
    self.assertEqual(cat1, cat)
    self.assertEqual(cat1.name, 'Tom')
    self.assertEqual(cat1.naps, 18)
    self.assertEqual(cat1.sound, 'purr')

  def testExpandoPoly(self):
    # Like testPolyExpando, but switch the order of the base classes.
    # It should work either way.
    class Animal(model.Expando, PolyModel):
      pass
    class Mammal(Animal):
      pass
    cat = Mammal(name='Tom', naps=18, sound='purr')
    cat1 = cat.put().get()
    self.assertFalse(cat1 is cat)
    self.assertEqual(cat1, cat)
    self.assertEqual(cat1.name, 'Tom')
    self.assertEqual(cat1.naps, 18)
    self.assertEqual(cat1.sound, 'purr')

  def testInheritance(self):
    # Tests focused on the inheritance model, including diamond inheritance.
    class NamedThing(model.Model):
      name = model.StringProperty()
    class Animal(PolyModel, NamedThing):
      legs = model.IntegerProperty(default=4)
    class Canine(Animal):
      pass
    class Dog(Canine):
      breed = model.StringProperty(default='mutt')
    class Wolf(Canine):
      mythical = model.BooleanProperty(default=False)
    class Feline(Animal):
      sound = model.StringProperty()
    class Cat(Feline):
      naps = model.IntegerProperty()
    class Panther(Feline):
      pass
    class Monster(Dog, Cat):
      ancestry = model.StringProperty()
    class Ghoul(Monster, model.Expando):
      pass

    k9 = Canine(name='Reynard')
    self.assertEqual(k9.legs, 4)
    self.assertEqual(k9._get_kind(), 'Animal')
    self.assertEqual(k9._class_name(), 'Canine')
    self.assertEqual(k9._class_key(), ['Animal', 'Canine'])

    tom = Cat(name='Tom', naps=12, sound='purr')
    self.assertTrue(isinstance(tom, Cat))
    self.assertTrue(isinstance(tom, Feline))
    self.assertTrue(isinstance(tom, Animal))
    self.assertTrue(isinstance(tom, PolyModel))
    self.assertEqual(tom.naps, 12)
    self.assertEqual(tom.sound, 'purr')
    self.assertEqual(tom.legs, 4)
    self.assertEqual(tom._get_kind(), 'Animal')
    self.assertEqual(tom._class_name(), 'Cat')
    self.assertEqual(tom._class_key(), ['Animal', 'Feline', 'Cat'])

    fido = Wolf(name='Warg')
    self.assertEqual(fido._get_kind(), 'Animal')
    self.assertEqual(fido._class_name(), 'Wolf')
    self.assertEqual(fido._class_key(), ['Animal', 'Canine', 'Wolf'])
    self.assertRaises(AttributeError, lambda: fido.breed)

    scary = Ghoul(name='Westminster', book='The Graveyard Book')
    self.assertEqual(scary.ancestry, None)
    self.assertEqual(scary._get_kind(), 'Animal')
    self.assertEqual(scary._class_name(), 'Ghoul')
    self.assertEqual(scary._class_key(), ['Animal',
                                         'Feline', 'Cat',
                                         'Canine', 'Dog',
                                         'Monster', 'Ghoul'])

    k91 = k9.put().get()
    self.assertTrue(isinstance(k9, Canine))
    self.assertEqual(k9.name, 'Reynard')
    self.assertEqual(k9._get_kind(), 'Animal')
    self.assertEqual(k9._class_name(), 'Canine')
    self.assertEqual(k9._class_key(), ['Animal', 'Canine'])
    self.assertTrue(isinstance(k91, Canine))
    self.assertEqual(k91.name, 'Reynard')
    self.assertEqual(k91._get_kind(), 'Animal')
    self.assertEqual(k91._class_name(), 'Canine')
    self.assertEqual(k91._class_key(), ['Animal', 'Canine'])
    self.assertEqual(k91, k9)

    tom1 = tom.put().get()
    self.assertEqual(tom1, tom)
    fido1 = fido.put().get()
    self.assertEqual(fido1, fido)
    scary1 = scary.put().get()
    self.assertEqual(scary1, scary)
    self.assertEqual(scary1.book, 'The Graveyard Book')

  def testPickling(self):
    # Test that PolyModel instances are pickled and unpickled properly.
    global Animal, Dog
    class Animal(PolyModel):
      name = model.StringProperty()
    class Dog(Animal):
      breed = model.StringProperty()
    for proto in 0, 1, 2:
      fido = Dog(name='Fido', breed='chihuahua')
      s = pickle.dumps(fido, proto)
      fido1 = pickle.loads(s)
      self.assertEqual(fido1.name, 'Fido')
      self.assertEqual(fido1.breed, 'chihuahua')
      self.assertEqual(fido1.class_, ['Animal', 'Dog'])
      self.assertEqual(fido, fido1)

  def testClassNameOverride(self):
    # Test that overriding _class_name() works.
    class Animal(PolyModel):
      pass
    class Feline(Animal):
      pass
    class Cat(Feline):
      @classmethod
      def _class_name(cls):
        return 'Pussycat'
    tom = Cat()
    self.assertEqual(tom.class_, ['Animal', 'Feline', 'Pussycat'])
    tom.put()
    self.assertEqual(Cat.query().fetch(), [tom])

  def testEdgeCases(self):
    # Test some edge cases.
    self.assertEqual(PolyModel._get_kind(), 'PolyModel')


TOM_PB = """\
key <
  app: "_"
  path <
    Element {
      type: "Animal"
      id: 0
    }
  >
>
entity_group <
>
property <
  name: "class"
  value <
    stringValue: "Animal"
  >
  multiple: true
>
property <
  name: "class"
  value <
    stringValue: "Feline"
  >
  multiple: true
>
property <
  name: "class"
  value <
    stringValue: "Cat"
  >
  multiple: true
>
property <
  name: "name"
  value <
    stringValue: "Tom"
  >
  multiple: false
>
property <
  name: "purr"
  value <
    stringValue: "loud"
  >
  multiple: false
>
property <
  name: "whiskers"
  value <
    booleanValue: true
  >
  multiple: false
>
"""


class CompatibilityTests(test_utils.NDBTest):

  def testCompatibility(self):
    class Animal(PolyModel):
      name = model.StringProperty()
    class Feline(Animal):
      whiskers = model.BooleanProperty()
    class Cat(Feline):
      purr = model.StringProperty()
    tom = Cat(name='Tom', purr='loud', whiskers=True)
    tom._prepare_for_put()
    self.assertEqual(str(tom._to_pb()), TOM_PB)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
