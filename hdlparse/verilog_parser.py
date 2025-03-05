# -*- coding: utf-8 -*-
# Copyright © 2017 Kevin Thibedeau
# Distributed under the terms of the MIT license
from __future__ import print_function

import re, os, io, collections
from .minilexer import MiniLexer

'''Verilog documentation parser

This module provides functionality to parse Verilog HDL code and extract module definitions,
including their ports, parameters, and submodule instances. The parser handles:
- Module declarations with ports and parameters
- Submodule instantiations (both regular and parameterized)
- Comments (both line and block comments)
- Metacomments for documentation
- Port connections and parameter assignments
'''

verilog_tokens = {
  'root': [
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\bmodule\s*(\w+)\s*', 'module', 'module'),
    (r'//#+(.*)\n', 'metacomment'),
  ],
  'module': [
    (r'\s+', None),  # Skip whitespace first
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\bendmodule\b', 'end_module', '#pop'),  # Keep endmodule simple and high priority
    (r'parameter\s+(?:(signed|integer|realtime|real|time)\s+)?(\[[^]]+\])?', 'parameter_start', 'parameters'),
    (r'(input|inout|output)\s+(?:(reg|supply0|supply1|tri|triand|trior|tri0|tri1|wire|wand|wor|logic)\s+)?(?:(signed)\s+)?(\[[^]]+\])?', 'module_port_start', 'module_port'),
    (r'\b(generate|endgenerate)\b', None),  # Simply ignore generate keywords
    (r'\b(\w+)\s+#\s*\(', 'submodule_param_start', 'submodule_params'),  # Start of parameterized submodule
    (r'\b(\w+)\s+(\w+)\s*\(', 'submodule_start', 'submodule'),  # Regular submodule
    (r'//#\s*{{(.*)}}\n', 'section_meta'),
  ],
  'parameters': [
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\s*parameter\s+(?:(signed|integer|realtime|real|time)\s+)?(\[[^]]+\])?', 'parameter_start'),
    (r'\s*(\w+)\s*=\s*([^,;\s]+)\s*', 'param_item_with_value'),
    (r'\s*(\w+)[^),;]+', 'param_item'),
    (r',', None),
    (r'[);]', None, '#pop'),
    (r'//#\s*{{(.*)}}\n', 'section_meta'),
  ],
  'module_port': [
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\s*(input|inout|output)\s+(?:(reg|supply0|supply1|tri|triand|trior|tri0|tri1|wire|wand|wor)\s+)?(signed)?\s*(\[[^]]+\])?', 'module_port_start'),
    (r'\s*(\w+)\s*,?', 'port_param'),
    (r'[);]', None, '#pop'),
    (r'//#\s*{{(.*)}}\n', 'section_meta'),
  ],
  'submodule_params': [
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\s*\)\s*(\w+)\s*\(', 'submodule_param_end'),  # End of params, start of ports
    (r'\);', 'end_submodule', '#pop'),
    (r'\.[^,)]+', None),  # Parameter and Ports assignments
    (r',', None),
  ],
  'submodule': [
    (r'/\*', 'block_comment', 'block_comment'),
    (r'//.*\n', None),
    (r'\);', 'end_submodule', '#pop'),
    (r'\.[^,)]+', None),  # Ports assignments
  ],
  'block_comment': [
    (r'\s*\*/', 'end_comment', '#pop'),
  ],
}


VerilogLexer = MiniLexer(verilog_tokens)

class VerilogObject(object):
  '''Base class for parsed Verilog objects.
  
  Attributes:
    name (str): Name of the Verilog object
    kind (str): Type of the object (default: 'unknown')
    desc (str): Optional description/metacomment for the object
  '''
  def __init__(self, name, desc=None):
    self.name = name
    self.kind = 'unknown'
    self.desc = desc

class VerilogParameter(object):
  '''Parameter definition in a module.
  
  Attributes:
    name (str): Name of the parameter
    mode (str): Parameter mode (default: None)
    data_type (str): Data type of the parameter (e.g., 'wire', 'reg')
    default_value (str): Default value of the parameter
    desc (str): Optional description/metacomment for the parameter
  '''
  def __init__(self, name, mode=None, data_type=None, default_value=None, desc=None):
    self.name = name
    self.mode = mode
    self.data_type = data_type
    self.default_value = default_value
    self.desc = desc

  def __str__(self):
    param = '{} : {}'.format(self.name, self.data_type)
    if self.default_value is not None:
      param = '{} := {}'.format(param, self.default_value)
    return param

  def __repr__(self):
    return "VerilogParameter('{}')".format(self.name)

class VerilogPort(object):
  '''Port definition in a module.
  
  Attributes:
    name (str): Name of the port
    mode (str): Port mode ('input', 'output', or 'inout')
    data_type (str): Data type of the port (e.g., 'wire', 'reg')
    desc (str): Optional description/metacomment for the port
  '''
  def __init__(self, name, mode=None, data_type=None, desc=None):
    self.name = name
    self.mode = mode  # input, output, inout
    self.data_type = data_type  # wire, reg, etc.
    self.desc = desc

  def __str__(self):
    return '{} : {} {}'.format(self.name, self.mode, self.data_type)

  def __repr__(self):
    return "VerilogPort('{}')".format(self.name)

class VerilogSubModule(object):
  '''Submodule instance in a module.
  
  Attributes:
    module_type (str): Type/name of the submodule being instantiated
    instance_name (str): Name of the submodule instance
    port_connections (dict): Dictionary mapping port names to their connections
    desc (str): Optional description/metacomment for the submodule
  '''
  def __init__(self, module_type, instance_name, port_connections=None, desc=None):
    self.module_type = module_type
    self.instance_name = instance_name
    self.port_connections = port_connections if port_connections is not None else {}
    self.desc = desc

  def __str__(self):
    return f"{self.instance_name} ({self.module_type})"

  def __repr__(self):
    return f"VerilogSubModule('{self.instance_name}', '{self.module_type}')"

class VerilogModule(VerilogObject):
  '''Module definition in Verilog.
  
  Attributes:
    name (str): Name of the module
    ports (list): List of VerilogPort objects defining the module's ports
    generics (list): List of VerilogParameter objects defining the module's parameters
    sections (dict): Dictionary mapping section names to lists of port names
    submodules (list): List of VerilogSubModule objects defining the module's submodules
    desc (str): Optional description/metacomment for the module
  '''
  def __init__(self, name, ports, generics=None, sections=None, submodules=None, desc=None):
    VerilogObject.__init__(self, name, desc)
    self.kind = 'module'
    # Verilog params
    self.generics = generics if generics is not None else []
    self.ports = ports
    self.sections = sections if sections is not None else {}
    self.submodules = submodules if submodules is not None else []

  def __repr__(self):
    return "VerilogModule('{}') {}".format(self.name, self.ports)



def parse_verilog_file(fname):
  '''Parse a named Verilog file.

  Args:
    fname (str): Path to the Verilog file to parse.
  Returns:
    list: List of VerilogModule objects found in the file.
  '''
  with open(fname, 'rt') as fh:
    text = fh.read()
  return parse_verilog(text)

def parse_verilog(text):
  '''Parse a text buffer of Verilog code.

  This function parses Verilog code and extracts module definitions, including their
  ports, parameters, and submodule instances. It handles:
  - Module declarations with ports and parameters
  - Submodule instantiations (both regular and parameterized)
  - Comments (both line and block comments)
  - Metacomments for documentation
  - Port connections and parameter assignments

  Args:
    text (str): Source code to parse.
  Returns:
    list: List of VerilogModule objects found in the text.
  '''
  lex = VerilogLexer

  name = None
  kind = None
  mode = 'input'
  ptype = 'wire'  # Default type

  metacomments = []
  param_items = []

  generics = []
  ports = collections.OrderedDict()
  sections = []
  port_param_index = 0
  last_item = None

  # Submodule parsing variables
  current_submodule = None
  submodules = []

  objects = []
  
  for pos, action, groups in lex.run(text):
    if action == 'metacomment':
      if last_item is None:
        metacomments.append(groups[0])
      else:
        last_item.desc = groups[0]

    if action == 'section_meta':
      sections.append((port_param_index, groups[0]))

    elif action == 'module':
      kind = 'module'
      name = groups[0]
      generics = []
      ports = collections.OrderedDict()
      param_items = []
      sections = []
      port_param_index = 0
      submodules = []
      ptype = 'wire'  # Reset default type for new module

    elif action == 'submodule_param_start':
      module_type = groups[0]
      current_submodule = VerilogSubModule(module_type, None)  # Instance name will be set later

    elif action == 'submodule_param_end':
      instance_name = groups[0]
      if current_submodule:
        current_submodule.instance_name = instance_name

    elif action == 'submodule_start':
      module_type, instance_name = groups
      current_submodule = VerilogSubModule(module_type, instance_name)

    elif action == 'end_submodule':
      if current_submodule:
        submodules.append(current_submodule)
        current_submodule = None

    elif action == 'parameter_start':
      net_type, vec_range = groups

      new_ptype = 'wire'  # Default type for parameters
      if net_type is not None:
        new_ptype = net_type

      if vec_range is not None:
        new_ptype += ' ' + vec_range

      ptype = new_ptype

    elif action == 'param_item_with_value':
      pname, pvalue = groups
      pvalue = pvalue.strip()  # Remove any trailing whitespace
      generics.append(VerilogParameter(pname, 'in', ptype, pvalue))

    elif action == 'param_item':
      pname = groups[0].strip()  # Remove any trailing whitespace
      if pname and not any(p.name == pname for p in generics):  # Avoid duplicates
        generics.append(VerilogParameter(pname, 'in', ptype))

    elif action == 'module_port_start':
      new_mode, net_type, signed, vec_range = groups

      new_ptype = 'wire'  # Default type for ports
      if net_type is not None:
        new_ptype = net_type

      if signed is not None:
        new_ptype += ' ' + signed

      if vec_range is not None:
        new_ptype += ' ' + vec_range

      mode = new_mode
      ptype = new_ptype
      param_items = []

    elif action == 'port_param':
      pname = groups[0]
      param_items.append(pname)
      ports[pname] = VerilogPort(pname, mode, ptype)
      port_param_index += 1
      last_item = ports[pname]

    elif action == 'end_module':
      # Create sections dict from list of tuples
      sections_dict = {}
      last_pos = 0
      for pos, section in sections:
        if last_pos < len(ports):
          sections_dict[section] = list(ports.keys())[last_pos:pos]
        last_pos = pos

      # Create the module object and add it to objects list
      module = VerilogModule(name, list(ports.values()), generics, sections_dict, submodules)
      if metacomments:
        module.desc = '\n'.join(metacomments)
      objects.append(module)
      metacomments = []
  return objects


def is_verilog(fname):
  '''Identify file as Verilog by its extension.

  Args:
    fname (str): File name to check.
  Returns:
    bool: True when file has a Verilog extension (.v or .vlog).
  '''
  return os.path.splitext(fname)[1].lower() in ('.vlog', '.v')


class VerilogExtractor(object):
  '''Utility class that caches parsed Verilog objects.
  
  This class provides methods to parse Verilog files and text, with caching to avoid
  re-parsing the same files multiple times.
  '''
  def __init__(self):
    self.object_cache = {}

  def extract_objects(self, fname, type_filter=None):
    '''Extract objects from a source file.

    Args:
      fname (str): Name of file to read from.
      type_filter (class, optional): Object class to filter results (e.g., VerilogModule).
    Returns:
      list: List of parsed objects, optionally filtered by type.
    '''
    objects = []
    if fname in self.object_cache:
      objects = self.object_cache[fname]
    else:
      with io.open(fname, 'rt', encoding='utf-8') as fh:
        text = fh.read()
        objects = parse_verilog(text)
        self.object_cache[fname] = objects

    if type_filter:
      objects = [o for o in objects if isinstance(o, type_filter)]

    return objects


  def extract_objects_from_source(self, text, type_filter=None):
    '''Extract object declarations from a text buffer.

    Args:
      text (str): Source code to parse.
      type_filter (class, optional): Object class to filter results (e.g., VerilogModule).
    Returns:
      list: List of parsed objects, optionally filtered by type.
    '''
    objects = parse_verilog(text)

    if type_filter:
      objects = [o for o in objects if isinstance(o, type_filter)]

    return objects


  def is_array(self, data_type):
    '''Check if a type is an array type.

    Args:
      data_type (str): Data type to check.
    Returns:
      bool: True when the data type contains array dimensions (e.g., '[7:0]').
    '''
    return '[' in data_type

