package paymentSystem.impl;

public class CollectionGenerics {

    /*
    * TODO ArrayList vs LinkedList ?
    *  ans:- if you need to store data continuously and if we want to fetch data using index
    *        then using array list is good also if there is less insertion in the middle of list and less removal as well then
    *       go for arraylist
    *       If Insertion and deletion is more form the middle of the list then go for linked list .
    *
    * TODO HashMap vs TreeMap?
    *  ans : if we want to sort the data in the key value pair then we should use the tree map also both store data in key value pair
    *        tree map do now allow the null key and value where as hashmap allows the single null key and multiple null data.
    *           TreeMap is slower than HashMap but provides sorted keys and range operations.
    * TODO What is Generics in java
    *   ans : Generics allows you to write classes, interface and methods with a type parameter so the type is checked at compile time not
    *           run time
    *           type Safety (classCastException)
    *           cleaner code
    *           code reusability
    *
    *
    * TODO Question: What is the difference between fail-fast and fail-safe iterators?
    *  Ans:- fail fast throws Concurrent modification exception if the collection is modified while iterating the examples are
    *        ArrayList HashMap HashSet
    *        Fail Safe works on a copy/clone of the collection so they don't throw exception
    *        Examples CopyOnWriteArrayList ConcurrentHashMap
    *
    * Interview Tip: Always mention performance trade-offs: fail-safe iterators are slower because they copy the collection.
    *
    * TODO 🔥 Core Java Learning Summary – Today
1️⃣ OOP Concepts

We solidified your core object-oriented programming understanding, including:

Abstraction

Definition: Hiding implementation details and showing only functionality.

Implementation in Java:

abstract class → partial abstraction

interface → complete abstraction (with default & static methods from Java 8)

Exercise: Payment system (PaymentProcessor interface)

Encapsulation

Definition: Hiding internal data and providing controlled access via getters/setters.

Example: UserAccount class with private balance field.

Polymorphism

Achieved through interface implementations:

CreditCardPaymentProcessor and UPIPaymentProcessor both implement PaymentProcessor

Demonstrated runtime polymorphism: one reference type (PaymentProcessor) pointing to different implementations.

Default & Static Methods in Interface

default → provides reusable behavior for all implementations

static → utility methods belonging to the interface, callable without an object

2️⃣ Collections Framework & Generics
ArrayList vs LinkedList

ArrayList: Fast random access, slow insertion/deletion in middle

LinkedList: Slow random access, fast insertion/deletion in middle

HashMap vs TreeMap

HashMap: Unordered, allows one null key, multiple null values, O(1) average lookup

TreeMap: Sorted by keys, no null key, O(log n) lookup

Generics

Ensures type safety at compile time

Avoids casting

Allows code reuse with multiple types

Other Important Collection Concepts

Fail-fast vs Fail-safe iterators

Synchronized vs Concurrent Collections

Set, List, Map differences

PriorityQueue vs Queue

HashMap internals (buckets, collisions, treeification, load factor)

High-yield Interview Questions Covered

ArrayList vs Vector

HashSet vs TreeSet

LinkedHashMap differences

Iterator vs ListIterator

Importance of overriding equals() and hashCode()

3️⃣ Practical Exercises

Payment System Project:

Interfaces, default/static methods

Concrete implementations

Encapsulated UserAccount class

Next homework: Library Management System (OOP practice)
    *
    *
    *
    * */
}
