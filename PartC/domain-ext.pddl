(define (domain lunar-extended)
  (:requirements :strips :typing)

  (:types rover lander waypoint astronaut)

  (:predicates

    ;;rover and lander's state
    (belongs_to ?r - rover ?l - lander)
    (aboard ?r - rover)
    (at ?r - rover ?w - waypoint)
    (lander_at ?l - lander ?w - waypoint)
    (connected ?a - waypoint ?b - waypoint)

    ;;data memory constraints
    (mem_free ?r - rover)
    (has_image ?r - rover ?w - waypoint)
    (has_scan ?r - rover ?w - waypoint)
    (image_saved ?l - lander ?w - waypoint)
    (scan_saved ?l - lander ?w - waypoint)

    ;;sample handling
    (sample_at ?w - waypoint)
    (hands_free ?r - rover)
    (has_sample ?r - rover ?w - waypoint)
    (lander_free ?l - lander)
    (sample_stored ?l - lander ?w - waypoint)
    
    ;;Astronaut's state
    (astronaut_of ?a - astronaut ?l - lander)
    (in_dock ?a - astronaut)
    (in_ctrl ?a - astronaut)
  )

  (:action to_dock
    :parameters (?a - astronaut)
    :precondition (in_ctrl ?a)
    :effect (and (not (in_ctrl ?a)) (in_dock ?a))
  )

  (:action to_ctrl
    :parameters (?a - astronaut)
    :precondition (in_dock ?a)
    :effect (and (not (in_dock ?a)) (in_ctrl ?a))
  )

  (:action deploy
    :parameters (?r - rover ?l - lander ?w - waypoint ?a - astronaut)
    :precondition (and (belongs_to ?r ?l) (aboard ?r) (lander_at ?l ?w)
                       (astronaut_of ?a ?l) (in_dock ?a))            ;deployment requires asrtronaut in bay
    :effect (and (not (aboard ?r)) (at ?r ?w))
  )

  (:action move
    :parameters (?r - rover ?a - waypoint ?b - waypoint)
    :precondition (and (at ?r ?a) (connected ?a ?b))
    :effect (and (not (at ?r ?a)) (at ?r ?b))
  )

  (:action capture_image
    :parameters (?r - rover ?w - waypoint)
    :precondition (and (at ?r ?w) (mem_free ?r))
    :effect (and (has_image ?r ?w) (not (mem_free ?r)))
  )

  (:action perform_scan
    :parameters (?r - rover ?w - waypoint)
    :precondition (and (at ?r ?w) (mem_free ?r))
    :effect (and (has_scan ?r ?w) (not (mem_free ?r)))
  )

  (:action transmit_image
    :parameters (?r - rover ?l - lander ?w - waypoint ?a - astronaut)
    :precondition (and (belongs_to ?r ?l) (has_image ?r ?w)
                       (astronaut_of ?a ?l) (in_ctrl ?a))             ;transmission requires astronaut in control room
    :effect (and (image_saved ?l ?w) (not (has_image ?r ?w)) (mem_free ?r))
  )

  (:action transmit_scan
    :parameters (?r - rover ?l - lander ?w - waypoint ?a - astronaut)
    :precondition (and (belongs_to ?r ?l) (has_scan ?r ?w)
                       (astronaut_of ?a ?l) (in_ctrl ?a))             ;transmission requires astronaut in control room
    :effect (and (scan_saved ?l ?w) (not (has_scan ?r ?w)) (mem_free ?r))
  )

  (:action collect_sample
    :parameters (?r - rover ?w - waypoint)
    :precondition (and (at ?r ?w) (sample_at ?w) (hands_free ?r))
    :effect (and (has_sample ?r ?w) (not (sample_at ?w)) (not (hands_free ?r)))
  )

  (:action store_sample
    :parameters (?r - rover ?l - lander ?lw - waypoint ?sw - waypoint ?a - astronaut) ;astronaut must be in bay and the rover must physically travel to lander's waypoint
    :precondition (and (belongs_to ?r ?l) (lander_at ?l ?lw) (at ?r ?lw)
                       (has_sample ?r ?sw) (lander_free ?l)
                       (astronaut_of ?a ?l) (in_dock ?a))
    :effect (and (sample_stored ?l ?sw) (not (has_sample ?r ?sw))
                 (hands_free ?r) (not (lander_free ?l)))
  )
)