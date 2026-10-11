# Poner la aplicación online

Así se abre desde cualquier navegador, también el del móvil, con un enlace. Hay dos caminos.

> Lo único que no puede hacer nadie por ti es crear las cuentas (Streamlit y Supabase) y pulsar
> "Deploy": son tus cuentas.

## Camino 1: probarla ya (5 minutos, con datos de demostración)

Sirve para ver la app funcionando online. No lleva tus datos reales.

1. Entra en <https://share.streamlit.io> e inicia sesión con tu cuenta de **GitHub**. Autoriza el acceso
   a tus repositorios (también a los privados).
2. Pulsa **Create app** y elige **Deploy a public app from GitHub** (aunque el repositorio sea privado).
3. Rellena:
   - **Repository:** `mtarrida/Monitorizacion`
   - **Branch:** `claude/pensive-bardeen-yzq1bj` (o `main` cuando hayas aceptado los cambios)
   - **Main file path:** `app.py`
4. Abre **Advanced settings** → **Secrets** y pega esta única línea:
   ```toml
   ENERGIA_DEMO = "1"
   ```
5. Pulsa **Deploy**. En 2-3 minutos aparece el enlace (`https://algo.streamlit.app`). Ábrelo en el móvil.

Aviso: en este camino cualquiera con el enlace puede entrar, y lo que cambies se pierde al reiniciar
la app. Úsalo solo con la demostración. Para algo más serio, el camino 2.

## Camino 2: con tus datos reales, con contraseña y sin perderlos

### A. Base de datos en la nube (Supabase, plan gratuito)
1. Crea una cuenta en <https://supabase.com> y un proyecto nuevo. Elige una región de la UE
   (por ejemplo Frankfurt) y apunta la **contraseña de la base de datos**. Usa una sin símbolos raros
   (solo letras y números), para que la dirección salga bien.
2. En el proyecto, pulsa **Connect** y copia la dirección del **Transaction pooler**. Se parece a:
   `postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`
   Sustituye `[YOUR-PASSWORD]` por tu contraseña, sin corchetes. Esa es tu **dirección de base de datos**.

   Usa la del *pooler*, no la directa: Streamlit Cloud solo conecta por IPv4.

### B. Usuarios y contraseñas
En tu PC, dentro de la carpeta de la app, haz doble clic en **`Crear usuario.bat`**. Escribe el nombre y
una contraseña de al menos 10 caracteres (no se ve al escribir). Te imprime una línea como:
`maria = "pbkdf2_sha256$240000$..."`. Repite para cada persona y guarda las líneas.
La contraseña no se guarda en ningún sitio: solo una huella que no se puede deshacer.

### C. Publicar la app
Igual que el camino 1 (pasos 1 a 3), y en **Secrets** pega esto, con tus valores:

```toml
DATABASE_URL = "postgresql://postgres.xxxx:TU_CONTRASEÑA@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

[usuarios]
maria = "pbkdf2_sha256$240000$...$..."
```
Sin la tabla `[usuarios]`, la app se abre sin contraseña. Con ella, pide usuario y contraseña antes de
mostrar nada, y bloquea durante 10 minutos a quien falle 5 veces seguidas.

### D. Llevar tus datos a la nube
Haz esto **después** de que la app haya arrancado una vez (así se crean las tablas) y con la base vacía.
En tu PC, doble clic en **`Migrar a la nube.bat`**. Pega la dirección de la base de datos cuando la pida
(no se ve al escribir). Copia tus edificios, simulaciones y consumos de `database.db`. No modifica
`database.db`, y se niega a copiar si la nube ya tiene datos, para no duplicar nada.

### E. Usar la app
Abre el enlace desde el móvil o desde cualquier ordenador. Entra con tu usuario.

## Qué debes saber

- **La app se duerme** si nadie la usa durante un tiempo (plan gratuito). Al abrirla de nuevo tarda
  unos 30 segundos en despertar.
- **Al refrescar la página hay que volver a entrar.**
- **Copias de seguridad:** el plan gratuito de Supabase normalmente no incluye copias automáticas y puede
  pausar proyectos sin uso. Conserva tu `database.db` como copia de la última migración y revisa las
  condiciones actuales del plan.
- **Archivos subidos:** los datos de cada importación se guardan en la base de datos. Las copias de los
  archivos originales (CSV y .dat) se guardan en una carpeta que, online, no es permanente.
- **Datos de clientes:** quedan en servidores de terceros (Streamlit y Supabase). Revisa que encaja con
  la política de protección de datos de PGI. Elegir región UE ayuda.
- **El repositorio de GitHub debe ser privado.** Los nombres de clientes de `database.db` quedaron en el
  historial de GitHub de versiones antiguas.
- Los cambios que se hagan en GitHub en la rama elegida se despliegan solos.
