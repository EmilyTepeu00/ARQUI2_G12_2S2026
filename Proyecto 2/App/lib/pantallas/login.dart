import 'package:flutter/material.dart';

import '../sesion.dart';
import '../tema.dart';
import 'puerta.dart';

class PantallaLogin extends StatefulWidget {
  const PantallaLogin({super.key});

  @override
  State<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends State<PantallaLogin> {
  final _usuario = TextEditingController();
  final _clave = TextEditingController();
  String? _error;
  bool _verClave = false;

  void _ingresar() {
    FocusScope.of(context).unfocus();
    if (_usuario.text.trim().isEmpty || _clave.text.isEmpty) {
      setState(() => _error = 'Ingrese su usuario y contraseña');
      return;
    }
    final usuario = autenticar(_usuario.text, _clave.text);
    if (usuario == null) {
      setState(() => _error = 'Usuario o contraseña incorrectos');
      return;
    }
    _clave.clear();
    setState(() => _error = null);
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 350),
        pageBuilder: (_, a, _) => FadeTransition(opacity: a, child: PantallaPuerta(usuario: usuario)),
      ),
    );
  }

  @override
  void dispose() {
    _usuario.dispose();
    _clave.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FondoNoche(
        child: Stack(children: [
          // Halos de luz detrás de la tarjeta, como en el login web.
          const Positioned(top: 90, left: -80, child: _Halo(color: Color(0x734C6BFF), tamano: 300)),
          const Positioned(bottom: 120, right: -90, child: _Halo(color: Color(0x4D8B5CF6), tamano: 280)),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Vidrio(
                    padding: const EdgeInsets.fromLTRB(26, 28, 26, 26),
                    child: AutofillGroup(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        const _Marca(),
                        const SizedBox(height: 34),
                        const TituloDegradado('Bienvenido de nuevo'),
                        const SizedBox(height: 8),
                        const Text('Ingrese con su usuario de administrador u operador.', style: TextStyle(color: C.tinta2, fontSize: 14)),
                        const SizedBox(height: 28),
                        const _Etiqueta('Usuario'),
                        TextField(
                          controller: _usuario,
                          autofillHints: const [AutofillHints.username],
                          autocorrect: false,
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(hintText: 'admin'),
                        ),
                        const SizedBox(height: 18),
                        const _Etiqueta('Contraseña'),
                        TextField(
                          controller: _clave,
                          obscureText: !_verClave,
                          autofillHints: const [AutofillHints.password],
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _ingresar(),
                          decoration: InputDecoration(
                            hintText: '••••••••',
                            suffixIcon: IconButton(
                              tooltip: _verClave ? 'Ocultar contraseña' : 'Mostrar contraseña',
                              icon: Icon(_verClave ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: C.tenue, size: 20),
                              onPressed: () => setState(() => _verClave = !_verClave),
                            ),
                          ),
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 16),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                            decoration: BoxDecoration(color: C.error.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(14)),
                            child: Text(_error!, style: const TextStyle(color: C.error, fontSize: 14)),
                          ),
                        ],
                        const SizedBox(height: 24),
                        BotonPrimario(texto: 'Ingresar', onPressed: _ingresar),
                        const SizedBox(height: 20),
                        const Text('Incubadora inteligente · AYC2 Grupo 12', textAlign: TextAlign.center, style: TextStyle(color: C.tenue, fontSize: 12)),
                      ]),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) => Row(children: [
        Image.asset('assets/logo.png', width: 36, height: 36),
        const SizedBox(width: 10),
        const Text('SmartEgg', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, letterSpacing: -0.3)),
      ]);
}

class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Text(texto, style: const TextStyle(color: C.tenue, fontSize: 12.5, fontWeight: FontWeight.w500)),
      );
}

class _Halo extends StatelessWidget {
  const _Halo({required this.color, required this.tamano});
  final Color color;
  final double tamano;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(
          width: tamano,
          height: tamano,
          decoration: BoxDecoration(shape: BoxShape.circle, gradient: RadialGradient(colors: [color, color.withValues(alpha: 0)])),
        ),
      );
}
