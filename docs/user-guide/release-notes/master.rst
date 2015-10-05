=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* Multiple instances of ``pulp_celerybeat`` can now run simultaneously.
  If one of them goes down, another instance will dispatch scheduled tasks as usual.

Deprecation
-----------

Client Changes
--------------

* Tasks with complete states (except `canceled` state) can now be deleted. This can be done
  using `pulp-admin tasks purge` command.

Agent Changes
-------------

Bugs
----

Known Issues
------------


Upgrade Instructions for 2.7.x --> master
-----------------------------------------

Upgrade the packages using::

    sudo yum update

After yum completes you should migrate the database using::

    sudo -u apache pulp-manage-db

.. note::
    If using systemd, you need to reload the systemd process before restarting services. This can
    be done using::

        sudo systemctl daemon-reload

After migrating the database, restart `httpd`, `pulp_workers`, `pulp_celerybeat`, and
`pulp_resource_manager`.

Rest API Changes
----------------

* Tasks with complete states (except `canceled` state) can now be deleted.

Binding API Changes
-------------------

Plugin API Changes
------------------

