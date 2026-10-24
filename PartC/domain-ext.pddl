(define (domain lunar-extended)
  (:requirements :strips :typing)

  (:types
    rover lander waypoint - object
    data sample - object
    astronaut room - object
  )

  (:predicates
    (at ?r - rover ?w - waypoint)
    (lander_at ?l - lander ?w - waypoint)
    (connected ?w1 - waypoint ?w2 - waypoint)
    (deployed ?r - rover)
    (belongs_to ?r - rover ?l - lander)
    (data_at ?d - data ?w - waypoint)
    (has_data ?r - rover ?d - data)
    (data_transmitted ?d - data ?l - lander)
    (sample_at ?s - sample ?w - waypoint)
    (has_sample ?r - rover ?s - sample)
    (sample_stored ?s - sample ?l - lander)
    (in_room ?a - astronaut ?r - room ?l - lander)
    (is_docking_bay ?r - room)
    (is_control_room ?r - room)
  )

  (:action deploy
    :parameters (?r - rover ?l - lander ?w - waypoint ?a - astronaut ?room - room)
    :precondition (and (belongs_to ?r ?l) (lander_at ?l ?w) (not (deployed ?r)) (in_room ?a ?room ?l) (is_docking_bay ?room))
    :effect (and (deployed ?r) (at ?r ?w))
  )

  (:action move
    :parameters (?r - rover ?w1 - waypoint ?w2 - waypoint)
    :precondition (and (at ?r ?w1) (connected ?w1 ?w2))
    :effect (and (not (at ?r ?w1)) (at ?r ?w2))
  )

  (:action move_astronaut
    :parameters (?a - astronaut ?r1 - room ?r2 - room ?l - lander)
    :precondition (and (in_room ?a ?r1 ?l) (not (in_room ?a ?r2 ?l)))
    :effect (and (not (in_room ?a ?r1 ?l)) (in_room ?a ?r2 ?l))
  )

  (:action capture_image
    :parameters (?r - rover ?w - waypoint ?d - data)
    :precondition (and (at ?r ?w) (data_at ?d ?w) (not (has_data ?r ?d)) (forall (?d2 - data) (not (has_data ?r ?d2))))
    :effect (and (has_data ?r ?d) (not (data_at ?d ?w)))
  )

  (:action perform_scan
    :parameters (?r - rover ?w - waypoint ?d - data)
    :precondition (and (at ?r ?w) (data_at ?d ?w) (not (has_data ?r ?d)) (forall (?d2 - data) (not (has_data ?r ?d2))))
    :effect (and (has_data ?r ?d) (not (data_at ?d ?w)))
  )

  (:action transmit_data
    :parameters (?r - rover ?l - lander ?d - data ?a - astronaut ?room - room)
    :precondition (and (belongs_to ?r ?l) (has_data ?r ?d) (in_room ?a ?room ?l) (is_control_room ?room))
    :effect (and (data_transmitted ?d ?l) (not (has_data ?r ?d)))
  )

  (:action collect_sample
    :parameters (?r - rover ?w - waypoint ?s - sample)
    :precondition (and (at ?r ?w) (sample_at ?s ?w) (forall (?s2 - sample) (not (has_sample ?r ?s2))))
    :effect (and (has_sample ?r ?s) (not (sample_at ?s ?w)))
  )

  (:action store_sample
    :parameters (?r - rover ?l - lander ?s - sample ?w - waypoint ?a - astronaut ?room - room)
    :precondition (and (belongs_to ?r ?l) (lander_at ?l ?w) (at ?r ?w) (has_sample ?r ?s) (forall (?s2 - sample) (not (sample_stored ?s2 ?l))) (in_room ?a ?room ?l) (is_docking_bay ?room))
    :effect (and (sample_stored ?s ?l) (not (has_sample ?r ?s)))
  )
)