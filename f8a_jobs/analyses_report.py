from datetime import datetime
from cucoslib.setup_celery import init_celery

from selinon import StoragePool
from cucoslib.models import WorkerResult, Analysis, Package, Version, Ecosystem


def _add_query_datetime_constrains(query, from_date, to_date):
    if from_date:
        query = query.filter(Analysis.started_at.isnot(None))\
            .filter(Analysis.started_at > from_date)

    if to_date:
        query = query.filter(Analysis.started_at.isnot(None)) \
            .filter(Analysis.started_at < to_date)

    return query


def _get_analysis_base_query(db, ecosystem, from_date, to_date):
    query = db.session.query(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .filter(Ecosystem.name == ecosystem)
    return _add_query_datetime_constrains(query, from_date, to_date)


def _get_finished_analyses_count(db, ecosystem, from_date, to_date):
    query = _get_analysis_base_query(db, ecosystem, from_date, to_date)
    return query.filter(Analysis.finished_at.isnot(None)).count()


def _get_unfinished_analyses_count(db, ecosystem, from_date, to_date):
    query = _get_analysis_base_query(db, ecosystem, from_date, to_date)
    return query.filter(Analysis.finished_at.is_(None)).count()


def _get_unique_analyses_count(db, ecosystem, from_date, to_date):
    query = _get_analysis_base_query(db, ecosystem, from_date, to_date)
    return query.distinct(Version.id).count()


def _get_unique_finished_analyses_count(db, ecosystem, from_date, to_date):
    query = _get_analysis_base_query(db, ecosystem, from_date, to_date)
    return query.filter(Analysis.finished_at.isnot(None)).distinct(Version.id).count()


def _get_packages_count(db, ecosystem, from_date, to_date):
    # We need to make sure that there is at least one worker result for the given package as if the init task fails for
    # some reason, there will be created EPV entries but that package does not exist
    query = db.session.query(WorkerResult) \
        .join(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .distinct(Package.id) \
        .filter(Ecosystem.name == ecosystem)

    query = _add_query_datetime_constrains(query, from_date, to_date)
    return query.count()


def _get_versions_count(db, ecosystem, from_date, to_date):
    # See _get_packages_count comment why doing this.
    query = db.session.query(WorkerResult) \
        .join(Analysis) \
        .join(Version) \
        .join(Package) \
        .join(Ecosystem)\
        .distinct(Version.id) \
        .filter(Ecosystem.name == ecosystem)

    query = _add_query_datetime_constrains(query, from_date, to_date)
    return query.count()


def construct_analyses_report(ecosystem, from_date=None, to_date=None):
    """Construct analyses state report.
    
    :param ecosystem: name of the ecosystem
    :param from_date: datetime limitation
    :type from_date: datetime.datetime
    :param to_date: datetime limitation
    :type to_date: datetime.datetime
    :return: a dict describing the current system state
    :rtype: dict
    """
    report = {
        'report': {},
        'from_date': str(from_date) if from_date else None,
        'to_date': str(to_date) if to_date else None,
        'now': str(datetime.now())
    }

    # TODO: init only Selinon
    # there is required only Selinon configuration, we don't need to connect to queues,
    # but let's stick with this for now
    init_celery(result_backend=False)
    db = StoragePool.get_connected_storage('BayesianPostgres')

    finished_analyses = _get_finished_analyses_count(db, ecosystem, from_date, to_date)
    unfinished_analyses = _get_unfinished_analyses_count(db, ecosystem, from_date, to_date)

    report['report']['ecosystem'] = ecosystem
    report['report']['analyses'] = finished_analyses + unfinished_analyses
    report['report']['analyses_finished'] = finished_analyses
    report['report']['analyses_unfinished'] = unfinished_analyses
    report['report']['analyses_finished_unique'] = _get_unique_finished_analyses_count(db, ecosystem, from_date, to_date)
    report['report']['analyses_unique'] = _get_unique_analyses_count(db, ecosystem, from_date, to_date)
    report['report']['packages'] = _get_packages_count(db, ecosystem, from_date, to_date)
    report['report']['versions'] = _get_versions_count(db, ecosystem, from_date, to_date)

    return report
