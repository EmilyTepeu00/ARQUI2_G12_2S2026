import 'dart:ui';

import 'package:flutter/material.dart';

// Mismos tokens que el frontend web (Frontend/src/index.css).
abstract final class C {
  static const fondo = Color(0xFF070A18);
  static const superficie = Color(0xFF121933);
  static const tinta = Color(0xFFF2F4FB);
  static const tinta2 = Color(0xFFB4BAD0);
  static const tenue = Color(0xFF7C84A3);
  static const linea = Color(0x14FFFFFF);
  static const acento = Color(0xFF4C6BFF);
  static const acento2 = Color(0xFF8AA2FF);
  static const ok = Color(0xFF3DDC97);
  static const alerta = Color(0xFFF5B84A);
  static const error = Color(0xFFFF6B6B);
}

ThemeData temaSmartEgg() {
  final base = ThemeData(
    brightness: Brightness.dark,
    fontFamily: 'PlusJakartaSans',
    scaffoldBackgroundColor: C.fondo,
    colorScheme: const ColorScheme.dark(primary: C.acento, surface: C.superficie, error: C.error),
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(bodyColor: C.tinta, displayColor: C.tinta),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white.withValues(alpha: 0.04),
      hintStyle: const TextStyle(color: C.tenue),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.linea)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.linea)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: C.acento, width: 1.5)),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: const Color(0xF0121933),
      contentTextStyle: const TextStyle(fontFamily: 'PlusJakartaSans', color: C.tinta, fontSize: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: Color(0x1FFFFFFF))),
    ),
  );
}

// Cielo nocturno con halos azules y violetas, igual al fondo de la web.
class FondoNoche extends StatelessWidget {
  const FondoNoche({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    Widget halo(Alignment a, Color c, double radio) => Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(gradient: RadialGradient(center: a, radius: radio, colors: [c, c.withValues(alpha: 0)])),
          ),
        );
    return Stack(children: [
      const Positioned.fill(
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xFF070A18), Color(0xFF0A0F24), Color(0xFF0D1022)],
            ),
          ),
        ),
      ),
      halo(const Alignment(0.9, -1.1), const Color(0x593854DC), 1.0),
      halo(const Alignment(-1.1, 1.1), const Color(0x477846A0), 0.9),
      Positioned.fill(child: child),
    ]);
  }
}

// Tarjeta de vidrio.
class Vidrio extends StatelessWidget {
  const Vidrio({super.key, required this.child, this.destacada = false, this.padding = const EdgeInsets.all(20)});
  final Widget child;
  final bool destacada;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final radio = BorderRadius.circular(26);
    return Container(
      decoration: BoxDecoration(
        borderRadius: radio,
        boxShadow: [
          BoxShadow(
            color: destacada ? const Color(0x664C6BFF) : const Color(0x66000000),
            blurRadius: 40,
            spreadRadius: -18,
            offset: const Offset(0, 20),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: radio,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              borderRadius: radio,
              border: Border.all(color: destacada ? const Color(0x664C6BFF) : C.linea),
              color: C.superficie.withValues(alpha: destacada ? 0.7 : 0.55),
              gradient: destacada
                  ? const RadialGradient(
                      center: Alignment.topLeft,
                      radius: 1.4,
                      colors: [Color(0x734C6BFF), Color(0x00121933)],
                    )
                  : null,
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}

// Botón píldora con el degradado azul del botón primario de la web.
class BotonPrimario extends StatelessWidget {
  const BotonPrimario({super.key, required this.texto, required this.onPressed, this.icono, this.cargando = false});
  final String texto;
  final VoidCallback? onPressed;
  final IconData? icono;
  final bool cargando;

  @override
  Widget build(BuildContext context) {
    final activo = onPressed != null && !cargando;
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 150),
      opacity: activo ? 1 : 0.45,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          gradient: const LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xFF5B78FF), Color(0xFF3A55E6)]),
          boxShadow: activo ? const [BoxShadow(color: Color(0xAA4C6BFF), blurRadius: 24, spreadRadius: -8, offset: Offset(0, 8))] : null,
        ),
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: activo ? onPressed : null,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [
                if (cargando)
                  const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                else if (icono != null)
                  Icon(icono, size: 19, color: Colors.white),
                if (cargando || icono != null) const SizedBox(width: 10),
                Text(texto, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// Título con degradado azul → blanco, como los encabezados de la web.
class TituloDegradado extends StatelessWidget {
  const TituloDegradado(this.texto, {super.key, this.tamano = 30});
  final String texto;
  final double tamano;

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      shaderCallback: (r) => const LinearGradient(colors: [C.acento2, C.tinta, C.tinta], stops: [0, 0.55, 1]).createShader(r),
      child: Text(texto, style: TextStyle(fontSize: tamano, fontWeight: FontWeight.w600, letterSpacing: -0.6, color: Colors.white, height: 1.15)),
    );
  }
}

// Punto de estado con brillo.
class PuntoEstado extends StatelessWidget {
  const PuntoEstado(this.color, {super.key});
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: 9,
        height: 9,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle, boxShadow: [BoxShadow(color: color, blurRadius: 8)]),
      );
}
