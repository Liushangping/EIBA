#!/usr/bin/python

import clang.cindex
import re
import subprocess

intrinsic_types = {'__m64', '__m128', '__m128i', '__m128d'}
pointer_arg_matcher = re.compile(r'.*(__m64|__m128|__m128i|__m128d).*\*.*')
non_pointer_arg_matcher = re.compile(r'.*(__m64|__m128|__m128i|__m128d).*')
header = "//Do not edit this file, it's automatically generated."


class FuncDeclVisitor:
    """For a intrinsic function declaration, generate the implementatio"""

    def __init__(self):
        self.alreay_visited = set()
        self.macros = []
        # self.funcnames = []
        # self.funcimpls = []
        # self.taildefines = []

    def __call__(self, node):
        # ret, name, arg_types, arg_names = self.parse(node)
        old_ret, old_name, old_arg_types, old_arg_names = self.parse(node)
        if old_name in self.alreay_visited:
            return
        self.alreay_visited.add(old_name)
        new_ret = old_ret.replace('__m', '_pi__m')
        new_name = '_pi' + old_name
        new_arg_types, new_paras = [], []
        for t, n in zip(old_arg_types, old_arg_names):
            # new_arg_types.append(t.replace('__m', 'my__m'))
            if pointer_arg_matcher.match(t):
                new_paras.append('&' + self.quote(n) + '->native_obj')
            elif non_pointer_arg_matcher.match(t):
                new_paras.append(self.quote(n) + '.native_obj')
            else:
                new_paras.append(n)
        macro_head = '#define ' + new_name + self.quote(
            ','.join(old_arg_names))
        # impl = '#define ' + new_name + '(' + \
        #        ','.join(t + ' ' + n for t, n in zip(new_arg_types, old_arg_names)) + \
        #        ')'
        macro_impl = old_name + self.quote(','.join(new_paras))
        if old_ret in intrinsic_types:
            macro_impl = self.native_to_my_expr(macro_impl)
        # exprs = []
        # if old_ret in intrinsic_types:
        #     exprs.append(new_ret + ' tmp')
        #     exprs.append('tmp.native_obj=' + old_name + self.quote(','.join(new_paras)))
        #     exprs.append('tmp')
        # else:
        #     exprs.append(old_name + self.quote(','.join(new_paras)))
        # impl = define_head + ' ' + self.quote(','.join(exprs))
        # if old_ret in intrinsic_types:
        #     impl = new_ret + ' tmp;' + \
        #            'tmp.native_obj=' + impl + 'return tmp;'
        # elif 'void' != old_ret:
        #     impl = 'return ' + impl

        # cur_func = decl + '{' + impl + '}'
        # impl = define_head + define_impl
        # self.funcimpls.append(impl)
        # self.funcnames.append((old_name, new_name))
        # self.taildefines.append('#ifdef ' + old_name + '\n' +
        #                         '#undef ' + old_name + '\n' + '#endif\n'
        #                         '#define ' + old_name + self.quote(','.join(old_arg_names)) +
        #                         ' ' + new_name + self.quote(','.join(old_arg_names)))
        win32_macro = ' '.join(['#define', new_name, old_name])
        linux_macro = macro_head + macro_impl
        self.macros.append('\n'.join(
            ['#ifdef WIN32', win32_macro, '#else', linux_macro, '#endif']))

    @staticmethod
    def parse(node):
        ret = node.result_type.spelling
        arg_types = []
        arg_names = []
        for a in node.get_arguments():
            arg_types.append(a.type.spelling)
            arg_names.append(a.spelling)
        return ret, node.spelling, arg_types, arg_names

    @staticmethod
    def quote(name):
        return '(' + name + ')'

    @staticmethod
    def native_to_my_expr(expr):
        return 'from_native_obj' + FuncDeclVisitor.quote(expr)

    def result(self):
        return self.result


def visit_func_decls(node, visitor):
    """visit AST, for each function declaration node, call visitor"""
    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        visitor(node)
    for c in node.get_children():
        visit_func_decls(c, visitor)


if __name__ == '__main__':
    src, out = "sse.in", "sse_impl.h"
    code = 'class __m64{}; class __m128{}; class __m128i{}; class __m128d{};'
    with open(src, 'r') as f:
        code = code + ';'.join(f)
        code = code + ';'
        # for line in f:
        #     code = code + line + ';'

    index = clang.cindex.Index.create()
    unit = index.parse('tmp.cc', None, [('tmp.cc', code)])
    visitor = FuncDeclVisitor()
    visit_func_decls(unit.cursor, visitor)

    with open(out, 'w') as outfile:
        outfile.write(header + '\n')
        outfile.write('\n'.join(visitor.macros))
        outfile.write('\n')
        # outfile.write('\n'.join(visitor.funcimpls))
        # outfile.write('\n')
        # outfile.write('\n'.join(visitor.taildefines))
        # for old_name, new_name in visitor.funcnames:
        #     outfile.write('#ifdef ' + old_name + '\n')
        #     outfile.write('#undef ' + old_name + '\n')
        #     outfile.write('#endif\n')
        #     outfile.write('#define ' + old_name + ' ' + new_name + '\n')
    subprocess.check_call(['clang-format', '-i', out])