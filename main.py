"""
Archivo principal que inicia la aplicación de comparación de bases de datos Firebird.
Este es el punto de entrada de la aplicación.
"""

import sys
from PyQt5.QtWidgets import QApplication
from main_app import MainApp


def main():
    """
    Función principal que inicia la aplicación.
    """
    try:
        # Crear aplicación Qt
        app = QApplication(sys.argv)
        app.setApplicationName("Comparador Firebird")
        
        # Crear y mostrar ventana principal
        ventana = MainApp()
        ventana.show()
        
        # Ejecutar loop principal
        return app.exec_()
        
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())