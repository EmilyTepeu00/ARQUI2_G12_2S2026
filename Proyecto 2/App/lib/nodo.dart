import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_blue_classic/flutter_blue_classic.dart';

// Una línea del registro de actividad que se muestra en pantalla.
class Evento {
  Evento(this.texto, {this.error = false}) : hora = DateTime.now();
  final String texto;
  final bool error;
  final DateTime hora;
}

// Lectura que el nodo manda en la línea DATOS (IoT/main/bluetooth.cpp).
class Datos {
  const Datos(this.temperatura, this.humedad, this.encendido, this.alarma, this.espaciosLibres);
  final double temperatura;
  final double humedad;
  final bool encendido;
  final bool alarma;
  final int espaciosLibres;

  // "DATOS 37.5 55.0 1 0 12" -> Datos; null si la línea viene mal.
  static Datos? parse(String linea) {
    final p = linea.split(' ');
    if (p.length != 6) return null;
    final t = double.tryParse(p[1]), h = double.tryParse(p[2]), esp = int.tryParse(p[5]);
    if (t == null || h == null || esp == null) return null;
    return Datos(t, h, p[3] == '1', p[4] == '1', esp);
  }
}

// Mensaje legible para cada respuesta de error del firmware (IoT/main/bluetooth.h).
const _errores = {
  'ERR OPERADOR': 'El nodo no reconoce a este operador.',
  'ERR YA_ABIERTA': 'La puerta ya estaba abierta.',
  'ERR YA_CERRADA': 'La puerta ya estaba cerrada.',
  'ERR CMD': 'El nodo no entendió el comando.',
};

// Conexión con el HC-05 del nodo y protocolo de texto por líneas.
class Nodo extends ChangeNotifier {
  final _bt = FlutterBlueClassic();

  List<BluetoothDevice> dispositivos = [];
  BluetoothDevice? dispositivo;
  BluetoothConnection? _conexion;
  StreamSubscription<Uint8List>? _sub;
  Timer? _sondeo;
  Timer? _espera;
  String _buffer = '';

  bool conectando = false;
  bool esperando = false;
  bool? puertaAbierta; // null = aún no se sabe
  Datos? datos; // null = aún no llegó ninguna lectura
  final registro = <Evento>[];

  // Último error para mostrar como aviso; la pantalla lo consume.
  String? aviso;

  bool get conectado => _conexion?.isConnected ?? false;

  Future<void> cargarDispositivos() async {
    try {
      if (!await _bt.isEnabled) await _bt.turnOn();
      dispositivos = (await _bt.bondedDevices ?? [])..sort((a, b) => _esHc05(b) - _esHc05(a));
    } catch (e) {
      _avisar('No se pudo leer la lista de Bluetooth: $e');
    }
    notifyListeners();
  }

  // El HC-05 aparece primero en la lista.
  int _esHc05(BluetoothDevice d) => (d.name ?? '').toUpperCase().contains('HC-05') || (d.name ?? '').toUpperCase().contains('SMARTEGG') ? 1 : 0;

  Future<void> conectar(BluetoothDevice d) async {
    conectando = true;
    notifyListeners();
    try {
      final conexion = await _bt.connect(d.address);
      if (conexion == null || !conexion.isConnected) throw Exception('sin respuesta');
      _conexion = conexion;
      dispositivo = d;
      _sub = conexion.input?.listen(_recibir, onDone: _cerrada, onError: (_) => _cerrada());
      _agregar('Conectado a ${d.name ?? d.address}');
      _enviar('ESTADO');
      // El RFID también abre y cierra: se consulta el estado cada pocos segundos.
      _sondeo = Timer.periodic(const Duration(seconds: 3), (_) => _enviar('ESTADO'));
    } catch (e) {
      _avisar('No se pudo conectar con ${d.name ?? d.address}. ¿Está encendido el nodo?');
    } finally {
      conectando = false;
      notifyListeners();
    }
  }

  Future<void> desconectar() async {
    await _conexion?.close();
    _cerrada();
  }

  void abrir(String idOperador) => _accion('ABRIR $idOperador');
  void cerrar(String idOperador) => _accion('CERRAR $idOperador');

  void _accion(String comando) {
    if (!conectado || esperando) return;
    esperando = true;
    notifyListeners();
    _enviar(comando);
    _espera = Timer(const Duration(seconds: 5), () {
      if (!esperando) return;
      esperando = false;
      _avisar('El nodo no respondió. Revise la conexión.');
    });
  }

  void _enviar(String comando) {
    if (!conectado) return;
    try {
      _conexion!.writeString('$comando\n');
    } catch (_) {
      _cerrada();
    }
  }

  void _recibir(Uint8List datos) {
    _buffer += ascii.decode(datos, allowInvalid: true);
    while (_buffer.contains('\n')) {
      final i = _buffer.indexOf('\n');
      final linea = _buffer.substring(0, i).trim();
      _buffer = _buffer.substring(i + 1);
      if (linea.isNotEmpty) _procesar(linea);
    }
  }

  void _procesar(String linea) {
    switch (linea) {
      case 'OK ABIERTA':
        _terminarEspera();
        puertaAbierta = true;
        _agregar('Puerta abierta');
      case 'OK CERRADA':
        _terminarEspera();
        puertaAbierta = false;
        _agregar('Puerta cerrada');
      case 'ESTADO ABIERTA':
        puertaAbierta = true;
      case 'ESTADO CERRADA':
        puertaAbierta = false;
      default:
        if (linea.startsWith('DATOS ')) {
          datos = Datos.parse(linea) ?? datos;
          break;
        }
        final error = _errores[linea];
        if (error == null) return; // otra salida del nodo: se ignora
        _terminarEspera();
        _agregar(error, error: true);
        _avisar(error);
        // Si el error fue por estado, el siguiente ESTADO corrige la vista.
        _enviar('ESTADO');
    }
    notifyListeners();
  }

  void _terminarEspera() {
    esperando = false;
    _espera?.cancel();
  }

  void _cerrada() {
    final estaba = _conexion != null;
    _sondeo?.cancel();
    _espera?.cancel();
    _sub?.cancel();
    _conexion = null;
    _sub = null;
    _buffer = '';
    esperando = false;
    puertaAbierta = null;
    datos = null;
    if (estaba) _agregar('Conexión cerrada', error: true);
    notifyListeners();
  }

  void _agregar(String texto, {bool error = false}) {
    registro.insert(0, Evento(texto, error: error));
    if (registro.length > 20) registro.removeLast();
  }

  void _avisar(String texto) {
    aviso = texto;
    notifyListeners();
  }

  @override
  void dispose() {
    _conexion?.close();
    _cerrada();
    super.dispose();
  }
}
