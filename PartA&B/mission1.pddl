(define (problem lunar-mission-1)
  (:domain lunar)

  (:objects
    lander1 - lander
    rover1 - rover
    w1 w2 w3 w4 w5 w6 - waypoint
    image5 scan3 - data
    sample1 - sample
  )

  (:init
    (lander_at lander1 w2) 
    (belongs_to rover1 lander1)
    
    ; Figure 2 connections
    (connected w1 w2)
    (connected w1 w4)
    (connected w2 w3)
    (connected w3 w5)
    (connected w5 w1)

    (data_at image5 w5)
    (data_at scan3 w3)
    (sample_at sample1 w1)
  )

  (:goal
    (and
      (data_transmitted image5 lander1)
      (data_transmitted scan3 lander1)
      (sample_stored sample1 lander1)
    )
  )
)