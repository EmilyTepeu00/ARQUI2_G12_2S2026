import 'package:flutter/material.dart';
import 'package:flutter_blue_classic/flutter_blue_classic.dart';

import '../nodo.dart';
import '../sesion.dart';
import '../tema.dart';
import 'login.dart';

class PantallaPuerta extends StatefulWidget {
  const PantallaPuerta({super.key, required this.usuario});
  final Usuario usuario;

  @override
  State<PantallaPuerta> createState() => _PantallaPuertaState();
}

class _PantallaPuertaState extends State<PantallaPuerta> {
  final _nodo = Nodo();

  @override
  void initState() {
    super.initState();
    _nodo.addListener(_mostrarAviso);
    _nodo.cargarDispositivos();
  }

  void _mostrarAviso() {
    final aviso = _nodo.aviso;
    if (aviso == null || !mounted) return;
    _nodo.aviso = null;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(aviso)));
  }

  Future<void> _salir() async {
    await _nodo.desconectar();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const PantallaLogin()));
  }

  @override
  void dispose() {
    _nodo.removeListener(_mostrarAviso);
    _nodo.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FondoNoche(
        child: SafeArea(
          child: ListenableBuilder(
            listenable: _nodo,
            builder: (context, _) => RefreshIndicator(
              onRefresh: _nodo.cargarDispositivos,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 32),
                children: [
                  _Encabezado(usuario: widget.usuario, onSalir: _salir),
                  const SizedBox(height: 26),
                  const TituloDegradado('Control de puerta'),
                  const SizedBox(height: 6),
                  const Text('Abra o cierre la incubadora por Bluetooth.', style: TextStyle(color: C.tinta2, fontSize: 14)),
                  const SizedBox(height: 22),
                  _TarjetaPuerta(nodo: _nodo, usuario: widget.usuario),
                  if (_nodo.datos != null) ...[
                    const SizedBox(height: 16),
                    _TarjetaIncubadora(datos: _nodo.datos!),
                  ],
                  const SizedBox(height: 16),
                  _TarjetaConexion(nodo: _nodo),
                  if (_nodo.registro.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _TarjetaActividad(registro: _nodo.registro),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Encabezado extends StatelessWidget {
  const _Encabezado({required this.usuario, required this.onSalir});
  final Usuario usuario;
  final VoidCallback onSalir;

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Image.asset('assets/logo.png', width: 32, height: 32),
      const SizedBox(width: 8),
      const Text('SmartEgg', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, letterSpacing: -0.3)),
      const Spacer(),
      Container(
        padding: const EdgeInsets.fromLTRB(4, 4, 4, 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: C.linea),
        ),
        child: Row(children: [
          Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [C.acento2, C.acento]),
            ),
            child: Text(usuario.nombre[0].toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Colors.white)),
          ),
          const SizedBox(width: 8),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(usuario.nombre, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
            Text(usuario.rol, style: const TextStyle(fontSize: 10.5, color: C.tenue)),
          ]),
          IconButton(
            tooltip: 'Cerrar sesión',
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.logout_rounded, size: 17, color: C.tenue),
            onPressed: onSalir,
          ),
        ]),
      ),
    ]);
  }
}

class _TarjetaPuerta extends StatelessWidget {
  const _TarjetaPuerta({required this.nodo, required this.usuario});
  final Nodo nodo;
  final Usuario usuario;

  @override
  Widget build(BuildContext context) {
    final abierta = nodo.puertaAbierta;
    final (estado, color, icono) = switch (abierta) {
      true => ('Abierta', C.alerta, Icons.lock_open_rounded),
      false => ('Cerrada', C.ok, Icons.lock_rounded),
      null => (nodo.conectado ? 'Consultando…' : 'Sin conexión', C.tenue, Icons.lock_outline_rounded),
    };

    return Vidrio(
      destacada: true,
      padding: const EdgeInsets.all(24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Text('Puerta', style: TextStyle(color: C.tinta2, fontSize: 14, fontWeight: FontWeight.w500)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(999)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              PuntoEstado(color),
              const SizedBox(width: 7),
              Text(abierta == null ? 'desconocido' : 'en vivo', style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500)),
            ]),
          ),
        ]),
        const SizedBox(height: 22),
        Row(children: [
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 250),
            child: Icon(icono, key: ValueKey(icono), size: 46, color: color),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(estado, style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w600, letterSpacing: -1.2, height: 1)),
          ),
        ]),
        const SizedBox(height: 26),
        BotonPrimario(
          texto: abierta == true ? 'Cerrar puerta' : 'Abrir puerta',
          icono: abierta == true ? Icons.lock_rounded : Icons.lock_open_rounded,
          cargando: nodo.esperando,
          onPressed: abierta == null
              ? null
              : () => abierta ? nodo.cerrar(usuario.idNodo) : nodo.abrir(usuario.idNodo),
        ),
        const SizedBox(height: 12),
        Text(
          'Queda registrado como ${usuario.idNodo} · método bluetooth',
          textAlign: TextAlign.center,
          style: const TextStyle(color: C.tenue, fontSize: 12),
        ),
      ]),
    );
  }
}

class _TarjetaIncubadora extends StatelessWidget {
  const _TarjetaIncubadora({required this.datos});
  final Datos datos;

  @override
  Widget build(BuildContext context) {
    final (estado, color) = !datos.encendido
        ? ('Apagado', C.tenue)
        : datos.alarma
            ? ('Alarma', C.error)
            : ('Normal', C.ok);

    Widget dato(IconData icono, String valor, String etiqueta) => Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(icono, size: 18, color: C.acento2),
            const SizedBox(height: 8),
            Text(valor, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600, letterSpacing: -0.5, fontFeatures: [FontFeature.tabularFigures()])),
            Text(etiqueta, style: const TextStyle(color: C.tenue, fontSize: 12)),
          ]),
        );

    return Vidrio(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Text('Incubadora', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(999)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              PuntoEstado(color),
              const SizedBox(width: 7),
              Text(estado, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500)),
            ]),
          ),
        ]),
        const SizedBox(height: 18),
        Row(children: [
          dato(Icons.thermostat_rounded, '${datos.temperatura.toStringAsFixed(1)} °C', 'Temperatura'),
          dato(Icons.water_drop_outlined, '${datos.humedad.toStringAsFixed(1)} %', 'Humedad'),
          dato(Icons.egg_outlined, '${datos.espaciosLibres}', 'Espacios libres'),
        ]),
      ]),
    );
  }
}

class _TarjetaConexion extends StatelessWidget {
  const _TarjetaConexion({required this.nodo});
  final Nodo nodo;

  @override
  Widget build(BuildContext context) {
    return Vidrio(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          PuntoEstado(nodo.conectado ? C.ok : C.error),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              nodo.conectado ? 'Conectado a ${nodo.dispositivo?.name ?? 'nodo'}' : 'Nodo desconectado',
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
            ),
          ),
          if (nodo.conectado)
            _BotonSecundario(texto: 'Desconectar', onPressed: nodo.desconectar)
          else
            IconButton(
              tooltip: 'Actualizar lista',
              icon: const Icon(Icons.refresh_rounded, color: C.tinta2, size: 20),
              onPressed: nodo.cargarDispositivos,
            ),
        ]),
        if (!nodo.conectado) ...[
          const SizedBox(height: 4),
          const Text('Elija el módulo del nodo entre los dispositivos emparejados.', style: TextStyle(color: C.tenue, fontSize: 12.5)),
          const SizedBox(height: 14),
          if (nodo.dispositivos.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0x29FFFFFF)),
              ),
              child: const Text(
                'No hay dispositivos emparejados. Empareje el HC-05 desde los ajustes de Bluetooth del teléfono (clave 1234) y vuelva aquí.',
                style: TextStyle(color: C.tinta2, fontSize: 13, height: 1.4),
              ),
            )
          else
            for (final d in nodo.dispositivos) _FilaDispositivo(dispositivo: d, nodo: nodo),
        ],
      ]),
    );
  }
}

class _FilaDispositivo extends StatelessWidget {
  const _FilaDispositivo({required this.dispositivo, required this.nodo});
  final BluetoothDevice dispositivo;
  final Nodo nodo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Material(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: nodo.conectando ? null : () => nodo.conectar(dispositivo),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white.withValues(alpha: 0.06)),
                child: const Icon(Icons.bluetooth_rounded, size: 17, color: C.acento2),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(dispositivo.name ?? 'Sin nombre', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                  Text(dispositivo.address, style: const TextStyle(fontSize: 11.5, color: C.tenue)),
                ]),
              ),
              nodo.conectando
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: C.acento2))
                  : const Icon(Icons.chevron_right_rounded, color: C.tenue),
            ]),
          ),
        ),
      ),
    );
  }
}

class _TarjetaActividad extends StatelessWidget {
  const _TarjetaActividad({required this.registro});
  final List<Evento> registro;

  @override
  Widget build(BuildContext context) {
    String hora(DateTime t) => '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';
    return Vidrio(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Actividad', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        const Text('Lo que ha pasado en esta sesión', style: TextStyle(color: C.tenue, fontSize: 12)),
        const SizedBox(height: 12),
        for (final e in registro.take(8))
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(children: [
              PuntoEstado(e.error ? C.error : C.acento2),
              const SizedBox(width: 12),
              Expanded(child: Text(e.texto, style: TextStyle(fontSize: 13.5, color: e.error ? C.error : C.tinta2))),
              Text(hora(e.hora), style: const TextStyle(fontSize: 12, color: C.tenue, fontFeatures: [FontFeature.tabularFigures()])),
            ]),
          ),
      ]),
    );
  }
}

class _BotonSecundario extends StatelessWidget {
  const _BotonSecundario({required this.texto, required this.onPressed});
  final String texto;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => TextButton(
        onPressed: onPressed,
        style: TextButton.styleFrom(
          foregroundColor: C.tinta,
          backgroundColor: Colors.white.withValues(alpha: 0.05),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999), side: const BorderSide(color: C.linea)),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          textStyle: const TextStyle(fontFamily: 'PlusJakartaSans', fontSize: 13, fontWeight: FontWeight.w500),
        ),
        child: Text(texto),
      );
}
