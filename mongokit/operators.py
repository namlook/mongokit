#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010, Nicolas Clairon
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


class SchemaOperator(object):
    repr = None

    def __init__(self, *args):
        assert self.repr is not None
        self._operands = list(args)

    def __repr__(self):
        return str(self)

    def __iter__(self):
        for operand in self._operands:
            yield operand

    def __eq__(self, other):
        return type(self) == type(other) and self._operands == other._operands

    def validate(self, value):
        raise NotImplementedError


class OR(SchemaOperator):
    repr = 'or'

    def __init__(self, *args):
        super(OR, self).__init__(*args)

    def __str__(self):
        repr = ' %s ' % self.repr
        return '<'+repr.join([i.__name__ for i in self._operands]) + '>'

    def validate(self, value):
        return isinstance(value, tuple(self._operands))


class NOT(SchemaOperator):
    repr = 'not'

    def __init__(self, *args):
        super(NOT, self).__init__(*args)

    def __str__(self):
        repr = ', %s ' % self.repr
        return '<not '+repr.join([i.__name__ for i in self._operands]) + '>'

    def validate(self, value):
        return not isinstance(value, tuple(self._operands))


class IS(SchemaOperator):
    repr = 'is'

    def __init__(self, *args):
        super(IS, self).__init__(*args)

    def __str__(self):
        representation = ' or %s ' % self.repr
        return '<is '+representation.join([repr(i) for i in self._operands]) + '>'

    def validate(self, value):
        if value in self._operands:
            for op in self._operands:
                if value == op and isinstance(value, type(op)):
                    return True
        return False
