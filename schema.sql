use LendEase;

Create table Gerente (
Id_ge int auto_increment primary key,
correo_ge varchar (50),
contrasena_ge varchar (256),
genero_ge varchar (15),
edad_ge int,
apellido_paterno_ge varchar (15),
apellido_materno_ge varchar (15),
nombre_ge varchar (15)
);

create table Administrador (
Id_ad int auto_increment primary key,
correo_ad varchar (50),
contrasena_ad varchar (256),
genero_ad varchar (15),
edad_ad int,
apellido_paterno_ad varchar (15),
apellido_materno_ad varchar (15),
nombre_ad varchar (15),
pais_ad varchar (25),
estado_ad varchar (25),
municipio_ad varchar (25),
colonia_ad varchar (25),
calle_ad varchar (25),
numero_int_ad varchar (25),
numero_ext_ad varchar (25),
CURP_ad varchar (25),
RFC_ad varchar (25),
Id_ge int,
FOREIGN KEY (Id_ge) REFERENCES Gerente(Id_ge)
);


create table Solicitante (
Id_so int auto_increment primary key,
correo_so varchar (50),
contrasena_so varchar (256),
genero_so varchar (15),
edad_so int,
apellido_paterno_so varchar (15),
apellido_materno_so varchar (15),
nombre_so varchar (15),
pais_so varchar (25),
estado_so varchar (25),
municipio_so varchar (25),
colonia_so varchar (25),
calle_so varchar (25),
numero_int_so varchar (25),
numero_ext_so varchar (25),
CURP_so varchar (25),
RFC_so varchar (25),
Id_ge int,
Id_ad int,
FOREIGN KEY (Id_ge) REFERENCES Gerente(Id_ge),
FOREIGN KEY (Id_ad) REFERENCES Administrador(Id_ad)
);

create table Claves (
Id_cl int auto_increment primary key,
contenido_cl varchar (500),
validez varchar (20),
Id_ge int,
FOREIGN KEY (Id_ge) REFERENCES Gerente(Id_ge)
);

create table Credito (
Id_cr int auto_increment primary key,
importe_cr int,
periodicidad_cr enum('diario', 'semanal', 'quincenal', 'mensual', 'bimestral', 'trimestral'),
cantidad_pago_cr int,
estado_cr varchar (20),
interes_cr double,
Id_so int,
motivo_rechazo_cr varchar (300),
interes_cr DECIMAL(5, 2),
fecha_creacion DATE,
fecha_aprobacion DATE,
fecha_vencimiento DATE
foreign key (Id_so) references Solicitante(Id_so)
);

create table Metodo_de_pago (
Id_mp int auto_increment primary key,
tipo_mp enum('transferencia', 'deposito'),
Id_cr int,
foreign key (Id_cr) references Credito(Id_cr)
);

create table Sancion (
Id_sa int auto_increment primary key,
sancionAnId_sa int,
fecha_sa datetime,
estado varchar (20),
interese_sa double,
Id_cr int,
foreign key (Id_cr) references Credito(Id_cr)
);


create table Trabajo (
Id_tr int auto_increment primary key,
empresa_tr varchar (40),
sueldo_tr int,
tipo_nomina_tr varchar (30),
puesto_tr varchar (30),
antiguedad varchar (30),
Id_so int,
foreign key (id_so) references Solicitante(Id_so)
);

create table Mensaje (
Id_me int auto_increment primary key,
mensaje_me varchar (400),
hora_me time,
Id_ad int,
Id_ge int,
foreign key (Id_ad) references Administrador(Id_Ad),
foreign key (Id_ge) references Gerente(Id_ge)
);

create table Notificacion (
Id_no int auto_increment primary key,
notificacion_no varchar (300),
hora_no time,
Id_ad int,
Id_ge int,
foreign key (Id_ad) references Administrador(Id_Ad),
foreign key (Id_ge) references Gerente(Id_ge)
);

create table Administra_solicita_paga(
Id_ad int,
Id_so int,
foreign key (Id_ad) references Administrador(Id_Ad),
foreign key (Id_so) references Solicitante(Id_so)
);

CREATE TABLE ReestructuracionCredito (
    Id_re INT AUTO_INCREMENT PRIMARY KEY,
    Id_cr INT NOT NULL,
    nuevo_monto DECIMAL(10, 2),
    nuevo_plazo INT,
    estado VARCHAR(20) DEFAULT 'pendiente',
    comentario_solicitante TEXT,
    comentario_respuesta TEXT,
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Id_cr) REFERENCES Credito(Id_cr)
);

CREATE TABLE HistorialEstadosCredito (
    id SERIAL PRIMARY KEY,
    credito_id INT NOT NULL,
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50),
    fecha TIMESTAMP DEFAULT NOW(),
    comentario TEXT,
    FOREIGN KEY (credito_id) REFERENCES Credito(Id_cr)
);

CREATE TABLE Pagos (
    Id_pago INT PRIMARY KEY AUTO_INCREMENT,
    Id_cr INT,
    monto_pago DECIMAL(10, 2),
    fecha_vencimiento DATE,
    fecha_pago DATE,
    estado_pago VARCHAR(50), -- Pendiente, Pagado, Atrasado
    FOREIGN KEY (Id_cr) REFERENCES Credito(Id_cr)
);


INSERT INTO Gerente (correo_ge, contrasena_ge, genero_ge, edad_ge, apellido_paterno_ge, apellido_materno_ge, nombre_ge) VALUES ('ramueljb@gmail.com', 'scrypt:32768:8:1$IC7CfMr1BtZnh2Ta$2669a3c02c781fbfb76d9a348696332f6ed63065de946e5d5e99e7dbc174c373952b52cf40c4cb84c597e25f907139ae9088825a065581a6b1a39591b9fc298c', 'masculino', 18, 'Botello', 'Juarez', 'Samuel');

