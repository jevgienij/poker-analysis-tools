# see http://www.w3.org/TR/SVG/
#
# This is a somewhat incomplete and minimalistic SVG parser
# that can render to a pycairo context which should be adequate
# for most needs.
#
# It purpose is to create a way of rendering vector graphics easily
# in Python rather than being a general purposes SVG renderer.
#
# i.e. the SVG files are tailored to work with this parser.
#
# TODO: No reason why this can't be made a compliant SVG
# implementation, just needs the effort :-)
#
# Implementation is via xml.etree.ElementTree and the
# pyparsing declarative EBNF based string parser.
#

import xml.etree.ElementTree as ET
import math
from pyparsing import Word, Optional, CaselessLiteral, nums, oneOf, Combine, ZeroOrMore, srange, Dict, Suppress, Group, OneOrMore #@UnresolvedImport

# FIXME: The number rule might be more efficiently implemented as a regex.
# performance testing needed against both implementations.

commaWsp = Optional(',').suppress()

digitSequence = Word( nums )

sign = oneOf( '+ -' )

integerConstant = digitSequence

fractionalConstant = digitSequence + Optional( '.' +  digitSequence ) | '.' +  digitSequence 

exponent = oneOf( 'e E' ) + Optional( sign ) + digitSequence

def parseFloat( t):
    return float( t[0] ) 
number = Combine( Optional( sign ) + fractionalConstant + Optional( exponent ) )
number.setParseAction( parseFloat)

angle = number + ( CaselessLiteral('deg') | CaselessLiteral('grad') | CaselessLiteral('rad') )


class SvgMatrix(object):
    def __init__(self, a, b, c, d, e, f ):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
    def __eq__(a,b): #@NoSelf
        return a.a == b.a and a.b == b.b and a.c == b.c and a.d == b.d and a.e == b.e and a.f == b.f
    def __repr__(self):
        return 'matrix(' + str(self.a) +',' + str(self.b) + ',' + str(self.c) + ',' + str(self.d) + ',' + str(self.e) + ',' + str(self.f) +')'

class SvgTranslate(SvgMatrix):
    def __init__(self, tx, ty):
        SvgMatrix.__init__(self, 1, 0, 0, 1, tx, ty)
    def __repr__(self):
        return 'translate(' + str(self.e) + ',' + str(self.f) + ')'
    
class SvgScale(SvgMatrix):
    def __init__(self, sx, sy):
        SvgMatrix.__init__(self, sx, 0, 0, sy, 0, 0)
    def __repr__(self):
        return 'scale(' + str(self.a) + ',' + str(self.d) + ')'
    
class SvgRotate(SvgMatrix):
    def __init__(self, angle, cx, cy):
        cs = math.cos(angle)
        sn = math.sin(angle)
        SvgMatrix.__init__(self, cs, sn, -sn, cs, cx - cs*cx + sn*cy, cy - sn*cx - cs*cy )

class SvgSkewX(SvgMatrix):
    def __init__(self, angle ):
        tn = math.tan(angle)
        SvgMatrix.__init__(self, 1, 0, tn, 1, 0, 0)
    
class SvgSkewY(SvgMatrix):
    def __init__(self, angle ):
        tn = math.tan(angle)
        SvgMatrix.__init__(self, 1, tn, 0, 1, 0, 0)

matrix = 'matrix' + '(' + number('a') + commaWsp \
                + number('b') + commaWsp \
                + number('c') + commaWsp \
                + number('d') + commaWsp \
                + number('e') + commaWsp \
                + number('f') + ')'
matrix.setParseAction( lambda t : SvgMatrix( t.a, t.b, t.c, t.d, t.e, t.f ) )

translate = 'translate' + '(' + number('tx') + commaWsp + Optional( number('ty') ) + ')'
translate.setParseAction( lambda t : SvgTranslate( t.tx, t.ty ) )

scale = 'scale' + '(' + number('sx')  + commaWsp + Optional( number.setName('sy') )  + ')'
scale.setParseAction( lambda t : SvgScale( t.sx, t.sy ) )

rotate = 'rotate' + '(' + number('angle') + Optional( commaWsp + number('cx') + commaWsp + number('cy')  ) + ')'
rotate.setParseAction( lambda t : SvgRotate( t.angle, t.cx, t.cy ) )

skewX = 'skewX' + '(' + number('angle')  + ')'
skewX.setParseAction( lambda t : SvgSkewX( t.angle ) )

skewY = 'skewY' + '(' + number('angle')  + ')'
skewY.setParseAction( lambda t : SvgSkewY( t.angle ) )

transform = matrix | translate | scale | rotate | skewX | skewY

transformList = transform + ZeroOrMore( commaWsp + transform )

style = Dict( ZeroOrMore( Group( Word( srange('[a-zA-Z-]') ) + Suppress(':') + Word( srange('[0-9a-zA-z#.\'()]') )  + Optional(Suppress(';') )) ) )

pathCommand = Group( oneOf('M m')('command') + OneOrMore( number('x') + commaWsp + number('y') ) \
    |  oneOf( 'Z z' )('command') \
    |  oneOf( 'L l' )('command') + OneOrMore( number('x') + commaWsp + number('y') ) \
    |  oneOf( 'H h' )('command') + OneOrMore( number('x') ) \
    |  oneOf( 'V v' )('command') + OneOrMore( number('y') ) \
    |  oneOf( 'C c' )('command') + OneOrMore( number('x1') + commaWsp + number('y1') + commaWsp + number('x2') + commaWsp + number('y2') + commaWsp + number('x') + commaWsp + number('y') ) \
    |  oneOf( 'S s' )('command') + OneOrMore( number('x2') + commaWsp + number('y2') + commaWsp + number('x') + commaWsp +  number('y') ) \
    |  oneOf( 'Q q' )('command') + OneOrMore( number('x1') + commaWsp + number('y1') + commaWsp + number('x') + commaWsp + number('y') ) \
    |  oneOf( 'T t' )('command') + OneOrMore( number('x') + commaWsp + number('y') ) \
    |  oneOf( 'A a' )('command') + OneOrMore( number('rx') +commaWsp + number('ry') + commaWsp + number('x-axis-rotation')  + commaWsp + number('large-arc-flag') + commaWsp + number('sweep-flag') + commaWsp + number('x') + commaWsp + number('y') ) \
    )

path = OneOrMore( pathCommand )

shapeElements = [ 
          '{http://www.w3.org/2000/svg}g',
          '{http://www.w3.org/2000/svg}rect',
          '{http://www.w3.org/2000/svg}path' 
          ]

class SvgNode(object):
    tagParsers = {}
    
    @classmethod
    def registerTagParser(cls,name,cls_):
        cls.tagParsers[name] = cls_
        
    def __init__(self,root):
        self.children = []
        self.id = self.readAttr(root,'id')
        
    def addChild(self,child):
        self.children.append(child)
        
    def parseSubElements( self, root, tags):
        for el in root:
            if el.tag in tags:
                if self.tagParsers.has_key( el.tag ):
                    self.addChild( self.tagParsers[ el.tag ]( el ) )
                else:
                    raise "Unimplemented: " + el.tag
                
    def readAttr(self,el,attr):
        if el.attrib.has_key(attr):
            return el.attrib[attr]
        else:
            return None
    
    def parseAttr(self,parser,el,attr):
        a = self.readAttr( el, attr )
        if not a is None:
            res = parser.parseString(a)
            if len(res.keys()) > 0:
                return res.asDict()
            res = res.asList()
            if len(res) == 1:
                return res[0]
            else:
                return res
        else:
            return None
        
    def dumpChildren(self,indent):
        s = ''
        for c in self.children:
            s += c.dump( indent )
        return s
    
    def dump(self,indent):
        return indent * ' ' + 'SvgNode\n' + self.dumpChildren(indent+1)
    
    def __repr__(self):
        return self.dump(0)
    
    def render(self, renderer):
        for c in self.children:
            c.render(renderer)

class SvgRect(SvgNode):
    def __init__(self,root):
        super(SvgRect,self).__init__(root)
        self.width = self.parseAttr( number, root,'width')
        self.height = self.parseAttr( number, root, 'height')
        self.rx = self.parseAttr( number, root, 'rx')
        self.ry = self.parseAttr( number, root, 'ry')
        self.x = self.parseAttr( number, root, 'x')
        self.y = self.parseAttr( number, root, 'y')
        self.style = self.parseAttr( style, root, 'style')
        if self.rx is None:
            self.rx = 0.0
        if self.ry is None:
            self.ry = 0.0

    def render(self, renderer):
        renderer.setStyle( self.style )
        if self.rx == 0.0 and self.ry == 0.0:
            renderer.rectangle(self.x,self.y,self.width,self.height)
        else:
            renderer.roundedRectangle(self.x,self.y,self.width,self.height,self.rx,self.ry)

    def dump(self,indent):
        return indent * ' ' + 'Rect %s width=%s height=%s rx=%s ry=%s x=%s y=%s style=%s\n'%(self.id, self.width, self.height, self.rx, self.ry, self.x, self.y, self.style)  + self.dumpChildren(indent+1)

SvgNode.registerTagParser('{http://www.w3.org/2000/svg}rect', SvgRect) 

class SvgPath(SvgNode):
    def __init__(self,root):
        super(SvgPath,self).__init__(root)
        self.d = self.parseAttr(path, root,'d')
        self.transform = self.parseAttr(transformList,root,'transform')
        self.style = self.parseAttr(style, root,'style')
    
    def dump(self,indent):
        return indent * ' ' + 'Path %s transform=%s style=%s d=%s\n'%(self.id, self.transform, self.style, self.d) + self.dumpChildren(indent+1)

SvgNode.registerTagParser('{http://www.w3.org/2000/svg}path', SvgPath) 

class SvgGroup(SvgNode):
    def __init__(self,root):
        super(SvgGroup,self).__init__(root)
        self.transform = self.parseAttr(transformList,root,'transform')
        self.parseSubElements( root,shapeElements)
        
    def render(self, renderer):
        renderer.enterGroup( self.transform )
        super(SvgGroup,self).render(renderer)
        renderer.exitGroup()

    def dump(self,indent):
        return indent * ' ' + 'Group %s'%self.id + ' transform=' + str(self.transform)+ '\n' + self.dumpChildren(indent+1) 

SvgNode.registerTagParser('{http://www.w3.org/2000/svg}g', SvgGroup) 

class Svg(SvgNode):
    def __init__(self,root):
        super(Svg,self).__init__(root)
        self.parseSubElements( root,shapeElements)

    def dump(self,indent):
        return indent * ' ' + 'Svg %s\n'%self.id + self.dumpChildren(indent+1)

SvgNode.registerTagParser('{http://www.w3.org/2000/svg}svg', Svg)

def loadSvgFile(fileName):
    return Svg( ET.parse(fileName).getroot() )