"""Bounded numeric formula interpreter; no Python execution. Workflow: README.md."""
import math
import operator
import re
from scalar_math import (CONSTANTS, EXTRA_FUNCTIONS, compare, mod, navigator_round, navigator_floor, navigator_ceil)


TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z_0-9]*)|(<=|>=|==|!=|[+\-*/%^<>()?:,]))')
BINARY = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv,
          '%': operator.mod, '^': operator.pow, '<': operator.lt, '<=': operator.le,
          '>': operator.gt, '>=': operator.ge, '==': operator.eq, '!=': operator.ne}
FUNCTIONS = {'abs': (abs, 1, 1), 'min': (lambda *args: min(args), 1, 32),
             'max': (lambda *args: max(args), 1, 32), 'round': (round, 1, 2),
             'floor': (math.floor, 1, 1), 'ceil': (math.ceil, 1, 1),
             'sqrt': (math.sqrt, 1, 1), 'pow': (operator.pow, 2, 2),
             'log': (math.log, 1, 2), 'exp': (math.exp, 1, 1)}
# Higher values bind more tightly. Power is right-associative and precedes unary signs.
PRECEDENCE = {'or': 1, 'xor': 2, 'and': 3, '==': 4, '!=': 4,
              '<': 5, '<=': 5, '>': 5, '>=': 5, '+': 6, '-': 6,
              '*': 7, '/': 7, '%': 7, '^': 9}
COMPARISONS = {'<', '<=', '>', '>=', '==', '!='}
SYNTAXES = ('studio', 'navigator')


class ScoreExpression:
    """Parse only an allowlisted scalar grammar into an immutable expression tree."""
    def __init__(self, expression, aliases, syntax='studio'):
        if syntax not in SYNTAXES:
            raise ValueError('Choose Studio or Navigator scalar syntax.')
        self.syntax = syntax
        self.functions = {**FUNCTIONS, **EXTRA_FUNCTIONS}
        self.precedence = dict(PRECEDENCE)
        if syntax == 'navigator':
            self.functions.pop('nthRoot')  # Navigator lowercases the complete expression.
            self.functions.update(round=(navigator_round, 1, 2), floor=(navigator_floor, 1, 2), ceil=(navigator_ceil, 1, 2))
            self.precedence.update({operation: 4 for operation in COMPARISONS}, mod=7)
        if not isinstance(expression, str) or not expression.strip() or len(expression) > 512:
            raise ValueError('Enter a formula of 1–512 characters.')
        source = expression.strip()
        if syntax == 'navigator':
            source = source.lower()
        self.tokens, self.variables = [], set()
        position = 0
        while position < len(source):
            match = TOKEN.match(source, position)
            if not match:
                raise ValueError(f'Unsupported formula character at position {position + 1}.')
            self.tokens.append(next(group for group in match.groups() if group is not None))
            position = match.end()
        if len(self.tokens) > 128:
            raise ValueError('Formula is too complex (maximum 128 tokens).')
        self.tokens.append('END')
        self.position, self.aliases = 0, set(aliases)
        self.tree = self.parse(0, 0)
        if self.peek() != 'END':
            raise ValueError('Unexpected token: ' + self.peek())
        self.check_depth(self.tree)

    @staticmethod
    def number(value):
        if type(value) not in (int, float) or abs(value) > 1e300 or not math.isfinite(value):
            raise ValueError('Formula values must be finite real numbers within ±1e300.')
        return value

    def peek(self):
        return self.tokens[self.position]

    def take(self):
        value = self.peek()
        self.position += 1
        return value

    def require(self, value):
        if self.peek() != value:
            raise ValueError('Expected ' + value + ', found ' + self.peek())
        self.take()

    def parse(self, minimum, depth):
        if depth > 24:
            raise ValueError('Formula nesting exceeds 24 levels.')
        token = self.peek()
        if token == 'END':
            raise ValueError('Incomplete formula.')
        self.take()
        if token in ('+', '-', 'not'):
            # Studio keeps its earlier not precedence; Navigator binds not with unary signs.
            left = ('unary', token, self.parse(4 if token == 'not' and self.syntax == 'studio' else 8, depth + 1))
        elif token == '(':
            left = self.parse(0, depth + 1)
            self.require(')')
            if self.syntax == 'navigator':
                left = ('group', left)
        elif token[0].isdigit() or token[0] == '.':
            left = ('number', self.number(float(token)))
        elif token in self.functions and self.peek() == '(':
            self.take()
            args = []
            if self.peek() != ')':
                while True:
                    args.append(self.parse(0, depth + 1))
                    if self.peek() != ',':
                        break
                    self.take()
            self.require(')')
            _, low, high = self.functions[token]
            if not low <= len(args) <= high:
                raise ValueError(f'{token} requires {low}–{high} arguments.')
            left = ('call', token, *args)
        elif token in self.aliases:
            self.variables.add(token)
            left = ('variable', token)
        elif token in CONSTANTS:
            left = ('number', CONSTANTS[token])
        else:
            raise ValueError('Unknown variable, function or token: ' + token)
        while self.peek() in self.precedence and self.precedence[self.peek()] >= minimum:
            operation = self.take()
            priority = self.precedence[operation]
            right = self.parse(priority if operation == '^' else priority + 1, depth + 1)
            # Navigator chains compare adjacent operands and short-circuit.
            if self.syntax == 'navigator' and operation in COMPARISONS:
                left = (('chain', (*left[1], operation), *left[2:], right) if left[0] == 'chain' else
                        ('chain', (operation,), left, right))
                continue
            if operation in COMPARISONS and left[0] == 'binary' and left[1] in COMPARISONS:
                raise ValueError('Write chained comparisons explicitly, e.g. (a<b) and (b<c).')
            left = ('binary', operation, left, right)
        if minimum == 0 and self.peek() == '?':
            self.take()
            yes = self.parse(0, depth + 1)
            self.require(':')
            left = ('conditional', left, yes, self.parse(0, depth + 1))
        return left

    def check_depth(self, node, level=0):
        if level > 24:
            raise ValueError('Formula nesting exceeds 24 levels.')
        for child in node[1:]:
            if isinstance(child, tuple):
                self.check_depth(child, level + 1)

    def evaluate(self, scores):
        def power(left, right):
            # Bound integer/float exponent work before calling the math operation.
            if abs(right) > 10000:
                raise ValueError('Power exponent must be within ±10000.')
            return operator.pow(left, right)

        def visit(node):
            kind = node[0]
            if kind == 'number':
                return node[1]
            if kind == 'group':
                return visit(node[1])
            if kind == 'chain':
                previous = visit(node[2])
                for operation, child in zip(node[1], node[3:]):
                    following = visit(child)
                    if not compare(operation, previous, following):
                        return 0
                    previous = following
                return 1
            if kind == 'variable':
                if node[1] not in scores:
                    raise ValueError('Missing variable: ' + node[1])
                return self.number(scores[node[1]])
            if kind == 'conditional':
                return visit(node[2] if visit(node[1]) else node[3])
            operation = node[1]
            if kind == 'unary':
                value = visit(node[2])
                return int(not value) if operation == 'not' else self.number(-value if operation == '-' else value)
            if kind == 'call':
                values = [visit(child) for child in node[2:]]
                if operation == 'round' and len(values) == 2 and self.syntax == 'studio':
                    if values[1] != int(values[1]) or abs(values[1]) > 100:
                        raise ValueError('round precision must be an integer within ±100.')
                    values[1] = int(values[1])
                return self.number(power(*values) if operation == 'pow' else self.functions[operation][0](*values))
            left = visit(node[2])
            if operation == 'and':
                return int(bool(left) and bool(visit(node[3])))
            if operation == 'or':
                return int(bool(left) or bool(visit(node[3])))
            right = visit(node[3])
            if operation == 'xor':
                return int(bool(left) != bool(right))
            result = (power(left, right) if operation == '^' else
                      mod(left, right) if operation in ('%', 'mod') and self.syntax == 'navigator' else
                      BINARY[operation](left, right))
            return self.number(int(result) if type(result) is bool else result)
        try:
            return visit(self.tree)
        except (ArithmeticError, TypeError, ValueError) as error:
            raise ValueError('Invalid formula result: ' + str(error)) from error
