// Usuarios del login de la app.
class Usuario {
  const Usuario({required this.username, required this.password, required this.nombre, required this.rol, required this.idNodo});
  final String username;
  final String password;
  final String nombre;
  final String rol;
  final String idNodo;
}

const usuarios = [
  Usuario(username: 'admin', password: 'admin123', nombre: 'Administrador SmartEgg', rol: 'Administrador', idNodo: 'ADMIN'),
  Usuario(username: 'operador1', password: 'operador1', nombre: 'Operador 1', rol: 'Operador', idNodo: 'OP1'),
  Usuario(username: 'operador2', password: 'operador2', nombre: 'Operador 2', rol: 'Operador', idNodo: 'OP2'),
];

// Devuelve el usuario si las credenciales coinciden, o null.
Usuario? autenticar(String username, String password) {
  final u = username.trim().toLowerCase();
  for (final usuario in usuarios) {
    if (usuario.username == u && usuario.password == password) return usuario;
  }
  return null;
}
