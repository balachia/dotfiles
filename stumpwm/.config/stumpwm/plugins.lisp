;; audio
(load-module "amixer")

(amixer::defvolcontrol amixer-Master-5- "Master" "5%-")
(amixer::defvolcontrol amixer-Master-5+ "Master" "5%+")


;(defun polybar-groups ()
;  "Return string representation for polybar stumpgroups module"
;  (apply #'concatenate 'string
;         (mapcar
;          (lambda (g)
;            (let* ((name (string-upcase (group-name g)))
;                   (n-win (write-to-string (length (group-windows g))))
;                   (display-text (cond ((string-equal name "MAIN" ) "   MAIN ")
;                                       ((string-equal name "CANVAS") "   CANVAS ")
;                                       ((string-equal name "FLOAT") "   FLOAT ")
;                                       (t (concat "   " name "  ")))))
;              (if (eq g (current-group))
;                  (concat "%{F#ECEFF4 B#882E3440 u#8A9899 +u}" display-text "[" n-win "] " "%{F- B- u- -u}")
;                  (concat "%{F#8A9899}" display-text "[" n-win "] " "%{F-}"))))
;          (sort (screen-groups (current-screen)) #'< :key #'group-number))))

(defun polybar-groups ()
  ""
  (apply #'concatenate 'string
         (mapcar
           (lambda (g)
             (let* ((name (string-upcase (group-name g)))
                    (display-text (concat " " name " ")))
             (if (eq g (current-group))
               (concat "%{u#8A9899 +u}" display-text "%{u- -u}")
               (concat display-text))))
           (sort (screen-groups (current-screen)) #'< :key #'group-number))))


;; Update polybar group indicator
;(add-hook *new-window-hook* (lambda (win) (run-shell-command "polybar-msg hook stumpwmgroups 1")))
;(add-hook *destroy-window-hook* (lambda (win) (run-shell-command "polybar-msg hook stumpwmgroups 1")))
;(add-hook *focus-window-hook* (lambda (win lastw) (run-shell-command "polybar-msg hook stumpwmgroups 1")))
(add-hook *focus-group-hook* (lambda (grp lastg) (run-shell-command "polybar-msg hook stumpwmgroups 1")))

