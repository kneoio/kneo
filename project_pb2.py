# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: project.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rproject.proto\x12\x07project\"3\n\x0eProjectRequest\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\"\x1d\n\x0fProjectResponse\x12\n\n\x02id\x18\x01 \x01(\t2W\n\x12ProjectGrpcService\x12\x41\n\nAddProject\x12\x17.project.ProjectRequest\x1a\x18.project.ProjectResponse\"\x00\x42\'\n\x15io.kneo.projects.grpcB\x0cProjectProtoP\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'project_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\025io.kneo.projects.grpcB\014ProjectProtoP\001'
  _globals['_PROJECTREQUEST']._serialized_start=26
  _globals['_PROJECTREQUEST']._serialized_end=77
  _globals['_PROJECTRESPONSE']._serialized_start=79
  _globals['_PROJECTRESPONSE']._serialized_end=108
  _globals['_PROJECTGRPCSERVICE']._serialized_start=110
  _globals['_PROJECTGRPCSERVICE']._serialized_end=197
# @@protoc_insertion_point(module_scope)
