from controller import Robot
import math
import random

def run_robot():
    # ==========================================
    # 1. INITIALISATION
    # ==========================================
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())
    
    # Constantes physiques du iRobot Create
    MAX_SPEED = 16.0
    HALF_SPEED = 8.0
    WHEEL_RADIUS = 0.031
    AXLE_LENGTH = 0.271756 # Distance entre les deux roues

    # --- Moteurs ---
    left_motor = robot.getDevice("left wheel motor")
    right_motor = robot.getDevice("right wheel motor")
    left_motor.setPosition(float('inf'))
    right_motor.setPosition(float('inf'))
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)

    # --- Encodeurs (Capteurs de position des roues) ---
    left_position_sensor = robot.getDevice("left wheel sensor")
    right_position_sensor = robot.getDevice("right wheel sensor")
    left_position_sensor.enable(timestep)
    right_position_sensor.enable(timestep)

    # --- Bumpers (Capteurs de collision) ---
    bumper_left = robot.getDevice("bumper_left")
    bumper_right = robot.getDevice("bumper_right")
    bumper_left.enable(timestep)
    bumper_right.enable(timestep)

    # --- Capteurs de vide (Cliff sensors) ---
    cliff_sensors = [
        robot.getDevice("cliff_left"),
        robot.getDevice("cliff_front_left"),
        robot.getDevice("cliff_front_right"),
        robot.getDevice("cliff_right")
    ]
    for sensor in cliff_sensors:
        sensor.enable(timestep)

    # --- Récepteur (Pour détecter les murs virtuels) ---
    receiver = robot.getDevice("receiver")
    receiver.enable(timestep)

    # --- LED ---
    led_on = robot.getDevice("led_on")
    led_on.set(1) # Allume la LED pour montrer que le robot est actif

    # ==========================================
    # 2. FONCTIONS DE DÉPLACEMENT SPÉCIFIQUES
    # ==========================================

    def passive_wait(seconds):
        """Met le robot en pause tout en continuant la simulation physique."""
        start_time = robot.getTime()
        while start_time + seconds > robot.getTime():
            if robot.step(timestep) == -1:
                quit()

    def turn(angle):
        """Fait tourner le robot d'un angle précis en radians."""
        # On arrête d'abord les moteurs
        left_motor.setVelocity(0.0)
        right_motor.setVelocity(0.0)
        
        # On enregistre la position initiale des roues
        l_offset = left_position_sensor.getValue()
        r_offset = right_position_sensor.getValue()
        robot.step(timestep)
        
        # Détermine le sens (1.0 = gauche, -1.0 = droite)
        neg = -1.0 if angle < 0.0 else 1.0
        left_motor.setVelocity(neg * HALF_SPEED)
        right_motor.setVelocity(-neg * HALF_SPEED)
        
        orientation = 0.0
        
        # Boucle jusqu'à atteindre l'angle souhaité
        while orientation < (neg * angle):
            # Distance parcourue par chaque roue depuis le début de la rotation
            l = left_position_sensor.getValue() - l_offset
            r = right_position_sensor.getValue() - r_offset
            dl = l * WHEEL_RADIUS
            dr = r * WHEEL_RADIUS
            
            # Formule mathématique de l'odométrie
            orientation = neg * (dl - dr) / AXLE_LENGTH
            
            if robot.step(timestep) == -1:
                quit()
                
        # Arrêt à la fin de la rotation
        left_motor.setVelocity(0.0)
        right_motor.setVelocity(0.0)
        robot.step(timestep)

    # Petite pause avant de démarrer
    passive_wait(0.5)
    print("Contrôleur iRobot Create démarré.")

    # ==========================================
    # 3. BOUCLE PRINCIPALE (Le "Cerveau")
    # ==========================================
    while robot.step(timestep) != -1:
        
        # -- LECTURE DES CAPTEURS --
        mur_virtuel = receiver.getQueueLength() > 0
        
        collision_gauche = bumper_left.getValue() != 0.0
        vide_gauche = cliff_sensors[0].getValue() < 100.0 or cliff_sensors[1].getValue() < 100.0
        
        collision_droite = bumper_right.getValue() != 0.0
        vide_droite = cliff_sensors[3].getValue() < 100.0 or cliff_sensors[2].getValue() < 100.0
        vide_face = cliff_sensors[1].getValue() < 100.0 or cliff_sensors[2].getValue() < 100.0

        # -- ARBRE DE DÉCISION --
        if mur_virtuel:
            print("Mur virtuel !")
            turn(math.pi) # Demi-tour complet (Pi radians = 180 degrés)
            
        elif collision_gauche or vide_gauche:
            print("Obstacle à gauche !")
            # Recule un peu...
            left_motor.setVelocity(-HALF_SPEED)
            right_motor.setVelocity(-HALF_SPEED)
            passive_wait(0.5)
            # ...et tourne vers la droite d'un angle aléatoire
            turn(math.pi * random.random()) 
            
        elif collision_droite or vide_droite or vide_face:
            print("Obstacle à droite !")
            # Recule un peu...
            left_motor.setVelocity(-HALF_SPEED)
            right_motor.setVelocity(-HALF_SPEED)
            passive_wait(0.5)
            # ...et tourne vers la gauche d'un angle aléatoire
            turn(-math.pi * random.random())
            
        else:
            # Rien ne bloque, on avance à pleine vitesse
            left_motor.setVelocity(MAX_SPEED)
            right_motor.setVelocity(MAX_SPEED)

        # -- NETTOYAGE --
        # Il faut vider la mémoire du récepteur infrarouge à chaque itération
        while receiver.getQueueLength() > 0:
            receiver.nextPacket()

if __name__ == "__main__":
    run_robot()