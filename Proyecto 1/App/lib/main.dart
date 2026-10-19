import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'pantallas/login.dart';
import 'tema.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: C.fondo,
  ));
  runApp(const SmartEggApp());
}

class SmartEggApp extends StatelessWidget {
  const SmartEggApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartEgg',
      debugShowCheckedModeBanner: false,
      theme: temaSmartEgg(),
      home: const PantallaLogin(),
    );
  }
}
