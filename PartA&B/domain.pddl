(define (domain lunar)
  (:requirements :strips :typing)

  (:types
    rover lander waypoint - object
    data sample - object
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
  )

  (:action deploy
    :parameters (?r - rover ?l - lander ?w - waypoint)
    :precondition (and (belongs_to ?r ?l) (lander_at ?l ?w) (not (deployed ?r)))
    :effect (and (deployed ?r) (at ?r ?w))
  )

  (:action move
    :parameters (?r - rover ?w1 - waypoint ?w2 - waypoint)
    :precondition (and (at ?r ?w1) (connected ?w1 ?w2))
    :effect (and (not (at ?r ?w1)) (at ?r ?w2))
  )

  (:action capture_image
    :parameters (?r - rover ?w - waypoint ?d - data)
    :precondition (and (at ?r ?w) (data_at ?d ?w) (not (has_data ?r ?d))
                       (forall (?d2 - data) (not (has_data ?r ?d2))))
    :effect (and (has_data ?r ?d) (not (data_at ?d ?w)))
  )

  (:action perform_scan
    :parameters (?r - rover ?w - waypoint ?d - data)
    :precondition (and (at ?r ?w) (data_at ?d ?w) (not (has_data ?r ?d))
                       (forall (?d2 - data) (not (has_data ?r ?d2))))
    :effect (and (has_data ?r ?d) (not (data_at ?d ?w)))
  )

  (:action transmit_data
    :parameters (?r - rover ?l - lander ?d - data)
    :precondition (and (belongs_to ?r ?l) (has_data ?r ?d))
    :effect (and (data_transmitted ?d ?l) (not (has_data ?r ?d)))
  )

  (:action collect_sample
    :parameters (?r - rover ?w - waypoint ?s - sample)
    :precondition (and (at ?r ?w) (sample_at ?s ?w)
                       (forall (?s2 - sample) (not (has_sample ?r ?s2))))
    :effect (and (has_sample ?r ?s) (not (sample_at ?s ?w)))
  )

  (:action store_sample
    :parameters (?r - rover ?l - lander ?s - sample ?w - waypoint)
    :precondition (and (belongs_to ?r ?l) (lander_at ?l ?w) (at ?r ?w) (has_sample ?r ?s)
                       (forall (?s2 - sample) (not (sample_stored ?s2 ?l))))
    :effect (and (sample_stored ?s ?l) (not (has_sample ?r ?s)))
  )
)