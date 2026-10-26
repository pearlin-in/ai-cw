(define (problem lunar-mission-1)
  (:domain lunar)

  (:objects
    lander1 - lander
    rover1 - rover
    w1 w2 w3 w4 w5 - waypoint
  )

  (:init
    (belongs_to rover1 lander1)
    (lander_at lander1 w2)
    (aboard rover1)
    (mem_free rover1)
    (hands_free rover1)
    (lander_free lander1)

    (sample_at w1)

    ; Figure 2
    (connected w1 w2)
    (connected w1 w4)
    (connected w2 w3)
    (connected w4 w3)
    (connected w3 w5)
    (connected w5 w1)
  )

  (:goal (and
    (image_saved lander1 w5)
    (scan_saved lander1 w3)
    (sample_stored lander1 w1)
  ))
)