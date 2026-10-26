(define (problem lunar-mission-3)
  (:domain lunar-extended)

  (:objects
    lander1 lander2 - lander
    rover1 rover2 - rover
    w1 w2 w3 w4 w5 w6 - waypoint
    alice bob - astronaut
  )

  (:init
    (belongs_to rover1 lander1)
    (lander_at lander1 w2)
    (at rover1 w2)
    (mem_free rover1)
    (hands_free rover1)
    (lander_free lander1)

    (belongs_to rover2 lander2)
    (lander_at lander2 w6)
    (aboard rover2)
    (mem_free rover2)
    (hands_free rover2)
    (lander_free lander2)

    (sample_at w5)
    (sample_at w1)

    (connected w1 w2)
    (connected w2 w1)
    (connected w2 w3)
    (connected w2 w4)
    (connected w4 w2)
    (connected w3 w5)
    (connected w5 w3)
    (connected w5 w6)
    (connected w6 w4)

    (astronaut_of alice lander1)
    (astronaut_of bob lander2)
    (in_dock alice)
    (in_ctrl bob)
  )

  (:goal (and
    (image_saved lander1 w3)
    (scan_saved lander2 w4)
    (image_saved lander2 w2)
    (scan_saved lander1 w6)
    (sample_stored lander1 w5)
    (sample_stored lander2 w1)
  ))
)