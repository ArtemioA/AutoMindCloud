from re import I
import sympy

import IPython

DatosList = []
Documento = []
#https://widdowquinn.github.io/coding/update-pypi-package/

#_print_Symbol

def Inicializar(n):
  global DatosList,Orden,Estilo
  
  DatosList = []
  Orden = n
  Documento = []
  return DatosList,Orden
  
def search(symbolo):
  for c_element in DatosList:
    if c_element[0] == symbolo:
      if isinstance(c_element[1],float):#Si tenemos un numero
          return "("+str(c_element[1])+")"
      elif isinstance(c_element[1],int):#Si tenemos un float
          return "("+str(c_element[1])+")"
      elif c_element[1] != None:#Si tenemos una expresión
          return "("+sympy.latex(c_element[1])+")"
      else:
        return sympy.latex(symbolo)#Si es None
  return sympy.latex(symbolo)

def Redondear(expr):#Redondeamos la expresión.
  if isinstance(expr, sympy.Expr) or isinstance(expr, sympy.Float):
    Aproximacion = expr.xreplace(sympy.core.rules.Transform(lambda x: x.round(Orden), lambda x: isinstance(x, sympy.Float)))
  elif isinstance(expr,float) or isinstance(expr,int):
    Aproximacion = round(expr,Orden)
  else:
    Aproximacion = expr
  return Aproximacion

def D(elemento,color = "black"):#Por default se imprime en rojo, para indicar que es un derivado.
  global Documento

  print("")
  Tipo = None
  if isinstance(elemento,sympy.core.relational.Equality):#Si el elemento ingresado es una ecuación, entonces la identificamos
    Tipo = "Ecuacion"
  elif isinstance(elemento,list):#Si el elemento ingresado es un componente, entonces lo identificamos.
    Tipo = "Componente"
    c_componente = elemento
  
  if Tipo == "Ecuacion":#Si hemos identificado el elemento ingresado como una ecuación, entonces la imprimimos en rojo

    a = sympy.latex(elemento.args[0])

    b = "="

    c = sympy.latex(elemento.args[1])

    texto = a + b + c
    #texto = texto.replace("text", Estilo)

    IPython.display.display(IPython.display.Latex("\\textcolor{"+color+"}{"+texto+"}"))
    Documento.append(texto)

  if Tipo == "Componente":#Si hemos identificado el elemento ingresado como un componente, entonces lo imprimimos en rojo


    #if not isinstance(c_componente[0],str):#isinstance(c_componente[0],sy.core.symbol.Symbol) or isinstance(c_componente[0],sy.core.symbol.Symbol) :
    a = sympy.latex(c_componente[0])

    b = " = "

    if c_componente[1] == c_componente[0]:#== None:<---------------------------------------------------------------------------------------------------------------------------
      c = "?"
    else:
      c = sympy.latex(Redondear(c_componente[1]))
    
    texto = a + b + c
      #texto = texto.replace("text", Estilo)
    IPython.display.display(IPython.display.Latex("\\textcolor{"+color+"}{"+texto+"}"))
    Documento.append(texto)

#def E(expr,color = "red"):
#  DataRealSymbolList = []#Guarda en formato symbolo todos los Datos
#  for element in DatosList:
#    if (element[1] != None) :
#      word = "" #if isinstance(element[1],sy.Float) or isinstance(element[1],float) or isinstance(element[1],int) or isinstance(element[1],sy.core.numbers.Integer):
#      for letra in sympy.latex(Redondear(element[1])):
#        if letra == " ":
#          word = word+"~"
#        else:
#          word = word+letra
#      DataRealSymbolList.append([element[0],sympy.symbols("("+word+")")])
#    else:
#      #Es decir, si es un simbolo sin valor (None) o coleccion de simbolos. Entonces:
#      DataRealSymbolList.append([element[0],element[0]])
#  #display(DataRealSymbolList)

#  if isinstance(expr,sympy.core.relational.Equality):
#    texto = sympy.latex(expr)
#    for element in DataRealSymbolList:
#      texto = texto.replace(sympy.latex(element[0]), sympy.latex(element[1]))

#    #D(expr.subs(DataRealSymbolList))
#    IPython.display.display(IPython.display.Latex("\\textcolor{"+color+"}{"+texto+"}"))
  
#  if isinstance(expr,list):
#    texto = sympy.latex(expr[1])
#    for element in DataRealSymbolList:
#      texto = texto.replace(sympy.latex(element[0]), sympy.latex(element[1]))

#    texto = sympy.latex(expr[0]) +" = "+texto
#    #D([expr[0],expr[1].subs(DataRealSymbolList)])
#    IPython.display.display(IPython.display.Latex("\\textcolor{"+color+"}{"+texto+"}"))
#    #D([expr[0],sy.N(expr[1].subs(DatosList))])

def S(c_componente):#Guardar
  global DatosList
  dentro = False
  for element in DatosList:

    #Si es un elemento None, entonces guardamos de forma especial:
    if element[1] == None:
      element[1] = element[0] 

    if element[0] == c_componente[0]:
      element[1] = c_componente[1]
      dentro = True#Si el elemento ha sido guardado antes, entonces no lo volvemos a ingresar. Sino que sobre escribimos lo que dicho
      #componente significaba con el valor actual que se desea guardar.

      
  if dentro == False:
    
    DatosList.append(c_componente)#Si el elemento no estaba adentro, simplemente lo agregamos.

  #Renderizado Gris
  if c_componente[1] == None or dentro == False:
    D(c_componente,"black")#Hacemos un print renderizado en color gris para indicar que el elemento ha sido definido/guardado
  else:
    D(c_componente,"black")#Hacemos un print renderizado en color gris para indicar que el elemento ha sido definido/guardado

#def A(c_componente):#Actualizar
#  color = "red"
#  for element in DatosList:
#    if element[0] == c_componente[0]:
#      #Identificamos el componente en la lista de datos guardados
#      #Ahora actualizamos los valores
#      D(c_componente)
#      E([c_componente[0],c_componente[1]],color)
#      D([c_componente[0],c_componente[1].subs(DatosList)],color)
#      #D([c_componente[0],E(c_componente[1])],color)
#      #D([c_componente[0],element[1].subs(DatosList)],color)
#      element[1] = element[1].subs(DatosList)
#      return element#Sistema por Artemio Araya :)

def R(string):
  display(IPython.display.Latex(string))  

from AutoMindCloud.latemix import *

def E(expr,color ="black"):
  print("")
  if isinstance(expr,sympy.core.relational.Equality):#Si tenemos una igualdad
    izquierda = expr.args[0]
    derecha = expr.args[1]
    texto = latemix(izquierda) + " = " + latemix(derecha)
    return IPython.display.display(IPython.display.Latex(texto))
  elif isinstance(expr,list):#Si tenemos un componente
    texto = sympy.latex(expr[0]) + " = " + latemix(expr[1])
    return IPython.display.display(IPython.display.Latex(texto))
  elif isinstance(expr,sympy.core.mul.Mul):
    texto = latemix(expr)
    return IPython.display.display(IPython.display.Latex(texto))


