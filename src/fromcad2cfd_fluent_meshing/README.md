# Fluent Meshing Module

The current module implements the first bounded planning step before automated
Fluent Meshing work: a preflight gate that reads FastCFD/FastFluent pilot
evidence and decides whether Fluent Meshing preparation should proceed.

It does not launch Fluent, import geometry, generate a mesh, or write case/data
files.
