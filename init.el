(setq package-archives '(("melpa" . "http://melpa.milkbox.net/packages/")
                         ("org" . "http://orgmode.org/elpa/")
                         ("gnu" . "http://elpa.gnu.org/packages/")))

(require 'package)
(package-initialize)



(require 'evil)
(evil-mode 1)

;; Enable transient mark mode
(transient-mark-mode 1)

;; enable parens mode
(show-paren-mode)

;;;;Org mode configuration
;; Enable Org mode
(require 'org)
;; Make Org mode work with files ending in .org
;; (add-to-list 'auto-mode-alist '("\\.org$" . org-mode))
;; The above is the default in recent emacsen

;; git
(define-key evil-normal-state-map ",gs" 'magit-status)
(require 'evil-magit)

;; themes
(defun theme-light () (interactive)
       (load-theme 'material-light t))
(defun theme-dark () (interactive)
       (load-theme 'molokai t))

(defun toggle-theme ()
  (interactive)
  (let* ((ring '(theme-dark theme-light))
         (current (if (get 'theme-toggle 'state) (get 'theme-toggle 'state) -1))
         (next-idx (% (+ current 1) (length ring)))
         (next (nth next-idx ring))
         )
  (put 'theme-toggle 'state next-idx)
  (funcall next)))

(if (file-exists-p (expand-file-name "~/.theme"))
    (with-temp-buffer (insert-file-contents (expand-file-name "~/.theme"))
		      (if (string-equal (buffer-string) "light")
			  (theme-light)
			  (theme-dark)))
    (toggle-theme))

;; import vim keybinds
(define-key evil-normal-state-map ",tot" 'toggle-theme)
