# SmartEgg · App de acceso por Bluetooth

App Android (Flutter / Dart) para abrir y cerrar la puerta de la incubadora
desde el celular. Se conecta al módulo HC-05 del nodo y le manda los comandos
de texto que entiende el firmware (`IoT/main/bluetooth.h`).

El APK listo para instalar está en [`apk/smartegg.apk`](apk/smartegg.apk).

## Usuarios

Son los mismos del frontend web (los que crea el backend con `infra/.env`):

| Usuario     | Contraseña  | Abre como |
|-------------|-------------|-----------|
| `admin`     | `admin123`  | `ADMIN`   |
| `operador1` | `operador1` | `OP1`     |
| `operador2` | `operador2` | `OP2`     |

Están en `lib/sesion.dart`. El "abre como" es el id que recibe el Arduino y
debe existir en la tabla `OPERADORES` de `IoT/main/puerta.cpp`; con ese id
queda registrada la apertura en el backend, con `metodo: "bluetooth"`.

## Uso

1. Empareja el HC-05 desde los ajustes de Bluetooth del teléfono (clave `1234`).
2. Abre la app, inicia sesión y elige el HC-05 en la lista.
3. La tarjeta de la puerta muestra el estado real (se consulta cada 3 s, así
   que también refleja lo que se abra con tarjeta RFID) y el botón la abre o
   la cierra.

Solo Android: el HC-05 es Bluetooth clásico y iOS no permite usarlo.

## Compilar

```bash
flutter pub get
flutter build apk --release
# sale en build/app/outputs/flutter-apk/app-release.apk
```

El APK se firma con la llave de depuración de Flutter: sirve para instalarlo
directo en un teléfono, no para publicarlo en la Play Store.

## Archivos

- `lib/sesion.dart` · usuarios del login.
- `lib/nodo.dart` · conexión Bluetooth y protocolo con el Arduino.
- `lib/tema.dart` · colores y componentes con el estilo del frontend web.
- `lib/pantallas/` · login y control de puerta.
