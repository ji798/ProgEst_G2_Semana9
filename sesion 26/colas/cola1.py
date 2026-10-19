cola = []

def encolar(queue,element):
    queue.append(element)
    return queue

def desencolar(queue):
    if len(queue) == 0:
        return None
    return queue.pop(0)

def esta_vacia(queue):
    return len(queue) == 0

def mostrar_cola(queue):
    return str(queue)

encolar(cola, 3)
print(mostrar_cola(cola))
encolar(cola, 5)
print(mostrar_cola(cola))
encolar(cola, 34)
print(mostrar_cola(cola))
desencolar(cola)
print(mostrar_cola(cola))