(setq package-archives '(("melpa" . "http://melpa.milkbox.net/packages/")
                         ("org" . "http://orgmode.org/elpa/")
                         ("gnu" . "http://elpa.gnu.org/packages/")))

(require 'package)
(package-initialize)



(require 'evil)
(evil-mode 1)

;; Enable transient mark mode
(transient-mark-mode 1)

;;;;Org mode configuration
;; Enable Org mode
(require 'org)
;; Make Org mode work with files ending in .org
;; (add-to-list 'auto-mode-alist '("\\.org$" . org-mode))
;; The above is the default in recent emacsen

;; themes
(defun theme-toggle ()
  (interactive)
  (let* ((ring '(material material-light))
         (current (if (get 'theme-toggle 'state) (get 'theme-toggle 'state) -1))
         (next-idx (% (+ current 1) (length ring)))
         (next (nth next-idx ring))
         )
  (put 'theme-toggle 'state next-idx)
  (load-theme next t)))

(theme-toggle)

