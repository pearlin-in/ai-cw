(define (problem lunar-mission-3)
  (:domain lunar-extended)

  (:objects
    lander1 lander2 - lander
    rover1 rover2 - rover
    w1 w2 w3 w4 w5 w6 - waypoint
    image3 image2 - data
    scan4 scan6 - data
    sample5 sample1 - sample
    alice bob - astronaut
    l1_dock l1_ctrl - room
    l2_dock l2_ctrl - room
  )

  (:init
    (lander_at lander1 w2)
    (belongs_to rover1 lander1)
    (deployed rover1)
    (at rover1 w2)

    (lander_at lander2 w6)
    (belongs_to rover2 lander2)

    ; map connections
    (connected w1 w2)
    (connected w2 w1)
    (connected w2 w3)
    (connected w2 w4)
    (connected w4 w2)
    (connected w3 w5)
    (connected w5 w3)
    (connected w5 w6)
    (connected w6 w4)

    (data_at image3 w3)
    (data_at scan4 w4)
    (data_at image2 w2)
    (data_at scan6 w6)
    (sample_at sample5 w5)
    (sample_at sample1 w1)

    ; astronauts
    (is_docking_bay l1_dock)
    (is_control_room l1_ctrl)
    (is_docking_bay l2_dock)
    (is_control_room l2_ctrl)
    (in_room alice l1_dock lander1)
    (in_room bob l2_ctrl lander2)
  )

  (:goal
    (and
      (data_transmitted image3 lander1)
      (data_transmitted scan6 lander1)
      (data_transmitted scan4 lander2)
      (data_transmitted image2 lander2)
      (sample_stored sample5 lander1)
      (sample_stored sample1 lander2)
    )
  )
)